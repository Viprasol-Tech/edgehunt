"""Fair-value vs market mispricing.

When you have a model probability for an event, compare it to the market price
to find *mispricing*. If your fair value is 65% but YES is on offer at 50c, the
market is underpricing YES -- you buy YES. If your fair value is 30% but YES is
on offer at 50c, the market is overpricing YES -- you buy NO (which is cheap
relative to its true 70% chance).

For each market we pick the side with the larger fee-adjusted EV and, if that
EV is positive and the raw edge clears ``min_edge``, emit a ranked
:class:`Opportunity`.
"""

from __future__ import annotations

from collections.abc import Mapping

from edgehunt.ev import edge as raw_edge
from edgehunt.ev import expected_value
from edgehunt.fees import FeeModel, fee_for_venue
from edgehunt.kelly import stake as kelly_stake
from edgehunt.models import Market, Opportunity, OpportunityType, Side


def mispricing(
    market: Market,
    fair_probability: float,
    fee: FeeModel | None = None,
    bankroll: float = 1000.0,
    kelly_fraction_mult: float = 0.5,
    min_edge: float = 0.0,
) -> Opportunity | None:
    """Compare a model probability to market price and emit an edge signal.

    Args:
        market: The market to evaluate.
        fair_probability: Your model's YES probability (0..1).
        fee: Fee model; defaults to the venue's standard model.
        bankroll: Bankroll in dollars for Kelly stake sizing.
        kelly_fraction_mult: Fractional-Kelly multiplier (default half-Kelly).
        min_edge: Minimum pre-fee edge (probability points) required to emit.

    Returns:
        An :class:`Opportunity` for the better side if its fee-adjusted EV is
        positive and the edge clears ``min_edge``; else ``None``.
    """
    if not 0.0 <= fair_probability <= 1.0:
        raise ValueError("fair_probability must be in [0, 1]")
    fee = fee or fee_for_venue(market.venue)

    yes_ev = expected_value(fair_probability, market.yes_ask, Side.YES, fee)
    no_ev = expected_value(fair_probability, market.no_ask, Side.NO, fee)

    if yes_ev >= no_ev:
        side, price, ev_val = Side.YES, market.yes_ask, yes_ev
    else:
        side, price, ev_val = Side.NO, market.no_ask, no_ev

    side_edge = raw_edge(fair_probability, price, side)
    if ev_val <= 0.0 or side_edge < min_edge:
        return None

    s = kelly_stake(bankroll, fair_probability, price, kelly_fraction_mult, side)
    price_frac = price / 100.0
    profit_per_dollar = ev_val / price_frac if price_frac > 0 else 0.0
    return Opportunity(
        kind=OpportunityType.MISPRICING,
        venue=market.venue,
        question=market.question,
        description=(
            f"Fair {fair_probability * 100:.0f}% vs {side.value}@{price}c "
            f"-- buy {side.value}, edge {side_edge * 100:+.1f}pts"
        ),
        edge=side_edge,
        ev_per_contract=ev_val,
        profit_per_dollar=profit_per_dollar,
        stake=s,
        score=ev_val,
    )


def find_mispricings(
    markets: list[Market],
    fair_values: Mapping[str, float],
    bankroll: float = 1000.0,
    kelly_fraction_mult: float = 0.5,
    min_edge: float = 0.0,
) -> list[Opportunity]:
    """Find all mispricings for markets that have a fair-value estimate.

    Args:
        markets: Markets to evaluate.
        fair_values: Map of ``market.ticker`` -> model YES probability.
        bankroll: Bankroll in dollars.
        kelly_fraction_mult: Fractional-Kelly multiplier.
        min_edge: Minimum pre-fee edge required.

    Returns:
        Opportunities sorted by ``score`` (EV) descending.
    """
    found: list[Opportunity] = []
    for m in markets:
        fair = fair_values.get(m.ticker)
        if fair is None:
            continue
        opp = mispricing(m, fair, None, bankroll, kelly_fraction_mult, min_edge)
        if opp is not None:
            found.append(opp)
    found.sort(key=lambda o: o.score, reverse=True)
    return found


__all__ = ["find_mispricings", "mispricing"]
