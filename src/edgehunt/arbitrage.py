"""Arbitrage detection for binary prediction markets.

Two kinds of locked-in (risk-free) profit are detected:

**Single-market arbitrage (``YES + NO < $1``).**
    On one venue, if you can buy YES at ``yes_ask`` *and* NO at ``no_ask`` for a
    combined cost below $1, you are guaranteed $1 of payout no matter how the
    event resolves (exactly one leg pays). The fee-adjusted lock-in profit per
    pair is::

        profit = 1 - (yes_ask + no_ask)/100 - fee(yes_ask) - fee(no_ask)

    If that is positive it is free money. We require it to be strictly positive
    *after* fees -- a raw sum of 99c that costs 2c in fees is **not** an arb.

**Cross-venue arbitrage (same event, two venues).**
    The same event often trades at different prices on Kalshi vs Polymarket.
    Buy YES on whichever venue offers the cheaper ``yes_ask`` and NO on the
    other venue's cheaper ``no_ask``. Again exactly one leg pays $1, so::

        profit = 1 - (yes_ask_a + no_ask_b)/100 - fees

    We try both (YES@A / NO@B) and (YES@B / NO@A) and keep the better, positive,
    fee-adjusted combination.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from edgehunt.fees import FeeModel, fee_for_venue
from edgehunt.models import CENTS_PER_DOLLAR, Market, Opportunity, OpportunityType


def single_market_arbitrage(
    market: Market,
    fee: FeeModel | None = None,
    stake: float = 0.0,
) -> Opportunity | None:
    """Detect a fee-adjusted ``YES + NO < $1`` lock-in on one market.

    Args:
        market: The market to inspect.
        fee: Fee model; defaults to the venue's standard model.
        stake: Dollars to deploy (used to scale the reported stake field).

    Returns:
        An :class:`Opportunity` if a positive fee-adjusted lock-in exists,
        else ``None``.
    """
    fee = fee or fee_for_venue(market.venue)
    cost = (market.yes_ask + market.no_ask) / CENTS_PER_DOLLAR
    fees = fee.trade_fee(market.yes_ask, 1) + fee.trade_fee(market.no_ask, 1)
    profit = 1.0 - cost - fees
    if profit <= 0.0:
        return None

    invested = cost + fees
    profit_per_dollar = profit / invested if invested > 0 else 0.0
    return Opportunity(
        kind=OpportunityType.SINGLE_MARKET_ARB,
        venue=market.venue,
        question=market.question,
        description=(
            f"Buy YES@{market.yes_ask}c + NO@{market.no_ask}c "
            f"(cost {cost * 100:.0f}c + fees) locks ${profit:.3f}/pair"
        ),
        edge=profit,
        ev_per_contract=profit,
        profit_per_dollar=profit_per_dollar,
        stake=stake,
        score=profit_per_dollar,
    )


def cross_venue_arbitrage(
    market_a: Market,
    market_b: Market,
    fee_a: FeeModel | None = None,
    fee_b: FeeModel | None = None,
    stake: float = 0.0,
) -> Opportunity | None:
    """Detect cross-venue arbitrage for the same event on two venues.

    Buys the cheaper YES on one venue and the cheaper NO on the other so that
    exactly one leg pays $1. Tries both leg assignments and returns the better,
    positive, fee-adjusted result.

    Args:
        market_a: Same event on venue A.
        market_b: Same event on venue B.
        fee_a: Fee model for venue A (defaults to its standard model).
        fee_b: Fee model for venue B (defaults to its standard model).
        stake: Dollars to deploy (used to scale the reported stake field).

    Returns:
        An :class:`Opportunity` if a positive fee-adjusted lock-in exists,
        else ``None``.
    """
    if market_a.join_key != market_b.join_key:
        raise ValueError("markets do not describe the same event (join_key mismatch)")
    fee_a = fee_a or fee_for_venue(market_a.venue)
    fee_b = fee_b or fee_for_venue(market_b.venue)

    # Combo 1: YES on A, NO on B.
    cost_1 = (market_a.yes_ask + market_b.no_ask) / CENTS_PER_DOLLAR
    fees_1 = fee_a.trade_fee(market_a.yes_ask, 1) + fee_b.trade_fee(market_b.no_ask, 1)
    profit_1 = 1.0 - cost_1 - fees_1

    # Combo 2: YES on B, NO on A.
    cost_2 = (market_b.yes_ask + market_a.no_ask) / CENTS_PER_DOLLAR
    fees_2 = fee_b.trade_fee(market_b.yes_ask, 1) + fee_a.trade_fee(market_a.no_ask, 1)
    profit_2 = 1.0 - cost_2 - fees_2

    if profit_1 >= profit_2:
        profit, cost, fees = profit_1, cost_1, fees_1
        yes_venue, yes_px = market_a.venue, market_a.yes_ask
        no_venue, no_px = market_b.venue, market_b.no_ask
    else:
        profit, cost, fees = profit_2, cost_2, fees_2
        yes_venue, yes_px = market_b.venue, market_b.yes_ask
        no_venue, no_px = market_a.venue, market_a.no_ask

    if profit <= 0.0:
        return None

    invested = cost + fees
    profit_per_dollar = profit / invested if invested > 0 else 0.0
    return Opportunity(
        kind=OpportunityType.CROSS_VENUE_ARB,
        venue=f"{yes_venue}/{no_venue}",
        question=market_a.question,
        description=(
            f"Buy YES@{yes_px}c on {yes_venue} + NO@{no_px}c on {no_venue} locks ${profit:.3f}/pair"
        ),
        edge=profit,
        ev_per_contract=profit,
        profit_per_dollar=profit_per_dollar,
        stake=stake,
        score=profit_per_dollar,
    )


def find_cross_venue_arbs(
    markets: Iterable[Market],
    stake: float = 0.0,
) -> list[Opportunity]:
    """Find all cross-venue arbs across a pool of markets.

    Markets are grouped by ``join_key``; every distinct venue pair within a
    group is checked.

    Args:
        markets: Pool of markets from one or more venues.
        stake: Dollars to deploy per opportunity (for the stake field).

    Returns:
        Opportunities sorted by ``score`` descending.
    """
    groups: dict[str, list[Market]] = {}
    for m in markets:
        groups.setdefault(m.join_key, []).append(m)

    found: list[Opportunity] = []
    for group in groups.values():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if group[i].venue == group[j].venue:
                    continue
                opp = cross_venue_arbitrage(group[i], group[j], stake=stake)
                if opp is not None:
                    found.append(opp)
    found.sort(key=lambda o: o.score, reverse=True)
    return found


def find_single_market_arbs(
    markets: Sequence[Market],
    stake: float = 0.0,
) -> list[Opportunity]:
    """Find all single-market arbs in a sequence of markets, ranked."""
    found = [opp for m in markets if (opp := single_market_arbitrage(m, stake=stake)) is not None]
    found.sort(key=lambda o: o.score, reverse=True)
    return found


__all__ = [
    "cross_venue_arbitrage",
    "find_cross_venue_arbs",
    "find_single_market_arbs",
    "single_market_arbitrage",
]
