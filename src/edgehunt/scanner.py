"""The Scanner -- combine every detector into one ranked board.

Given a :class:`~edgehunt.feed.MarketFeed` (and optional fair values), the
scanner runs all three detectors -- single-market arb, cross-venue arb and
fair-value mispricing -- merges the results, filters by a minimum edge, and
returns a single list of :class:`~edgehunt.models.Opportunity` sorted so the
best edge is on top.

Arbitrage opportunities are ranked by fee-adjusted profit-per-dollar;
mispricings are ranked by EV. To make them comparable on one board we sort the
merged list by ``score`` with arbs given a slight precedence (risk-free beats
expected) when scores tie.
"""

from __future__ import annotations

from dataclasses import dataclass

from edgehunt.arbitrage import find_cross_venue_arbs, find_single_market_arbs
from edgehunt.fairvalue import find_mispricings
from edgehunt.feed import MarketFeed
from edgehunt.kelly import stake as kelly_stake
from edgehunt.models import Market, Opportunity, OpportunityType

# Risk-free arbs sort ahead of expected-value plays when scores are close.
_KIND_PRECEDENCE = {
    OpportunityType.CROSS_VENUE_ARB: 2,
    OpportunityType.SINGLE_MARKET_ARB: 2,
    OpportunityType.MISPRICING: 1,
}


@dataclass
class Scanner:
    """Run all edge detectors over a feed and rank the results.

    Args:
        feed: Any :class:`MarketFeed` (e.g. ``FakeFeed`` or a ``LiveFeed``).
        bankroll: Bankroll in dollars used for Kelly stake sizing.
        kelly_fraction: Fractional-Kelly multiplier (default half-Kelly).
        min_edge: Minimum edge to keep an opportunity. For arbs this is the
            fee-adjusted profit per pair (dollars); for mispricings it is the
            pre-fee edge in probability points.
    """

    feed: MarketFeed
    bankroll: float = 1000.0
    kelly_fraction: float = 0.5
    min_edge: float = 0.0

    def scan(self) -> list[Opportunity]:
        """Produce the ranked opportunity board."""
        markets: list[Market] = self.feed.fetch_markets()
        fair_values = self.feed.fair_values()

        # Arbitrage uses a fixed slice of bankroll as the illustrative stake.
        arb_stake = self.bankroll * self.kelly_fraction

        opps: list[Opportunity] = []
        opps.extend(
            o for o in find_single_market_arbs(markets, stake=arb_stake) if o.edge >= self.min_edge
        )
        opps.extend(
            o for o in find_cross_venue_arbs(markets, stake=arb_stake) if o.edge >= self.min_edge
        )
        opps.extend(
            find_mispricings(
                markets,
                fair_values,
                bankroll=self.bankroll,
                kelly_fraction_mult=self.kelly_fraction,
                min_edge=self.min_edge,
            )
        )

        opps.sort(
            key=lambda o: (_KIND_PRECEDENCE[o.kind], o.score),
            reverse=True,
        )
        return opps

    def best(self) -> Opportunity | None:
        """Return the single best opportunity, or ``None`` if none qualify."""
        ranked = self.scan()
        return ranked[0] if ranked else None


def recommended_stake(
    bankroll: float,
    win_probability: float,
    price_cents: int,
    kelly_fraction: float = 0.5,
) -> float:
    """Convenience wrapper around :func:`edgehunt.kelly.stake`."""
    return kelly_stake(bankroll, win_probability, price_cents, kelly_fraction)


__all__ = ["Scanner", "recommended_stake"]
