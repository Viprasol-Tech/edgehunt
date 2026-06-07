from __future__ import annotations

import pytest

from edgehunt.fairvalue import find_mispricings, mispricing
from edgehunt.models import Market, OpportunityType, Side


def _mkt(ticker: str, ya: int, na: int, venue: str = "kalshi") -> Market:
    return Market(
        venue=venue,
        ticker=ticker,
        question=f"q-{ticker}",
        yes_bid=max(1, ya - 2),
        yes_ask=ya,
        no_bid=max(1, na - 2),
        no_ask=na,
    )


def test_mispricing_buys_yes_when_underpriced() -> None:
    # Fair 55% vs YES at 33c -> strong YES edge.
    m = _mkt("FED", 33, 69)
    opp = mispricing(m, 0.55)
    assert opp is not None
    assert opp.kind is OpportunityType.MISPRICING
    assert "buy YES" in opp.description
    assert opp.edge > 0
    assert opp.stake > 0


def test_mispricing_buys_no_when_overpriced() -> None:
    # Fair 10% vs YES at 22c -> NO is cheap relative to true 90%.
    m = _mkt("OSCAR", 22, 79)
    opp = mispricing(m, 0.10)
    assert opp is not None
    assert "buy NO" in opp.description
    assert opp.edge > 0


def test_no_mispricing_when_efficient() -> None:
    # Fair 50% vs 51c both sides -> no positive EV after fees.
    m = _mkt("RAIN", 51, 51)
    assert mispricing(m, 0.50) is None


def test_min_edge_filters_small_edges() -> None:
    m = _mkt("GDP", 64, 38)
    # Fair 66% vs YES 64c -> only ~2pts edge; require 5pts.
    assert mispricing(m, 0.66, min_edge=0.05) is None


def test_mispricing_rejects_bad_probability() -> None:
    with pytest.raises(ValueError):
        mispricing(_mkt("X", 50, 51), 1.5)


def test_find_mispricings_ranks_by_ev() -> None:
    markets = [_mkt("FED", 33, 69), _mkt("GDP", 64, 38)]
    fair = {"FED": 0.55, "GDP": 0.66}
    opps = find_mispricings(markets, fair)
    assert len(opps) == 2
    # FED has the bigger edge so it should rank first.
    assert opps[0].question == "q-FED"
    assert opps[0].score >= opps[1].score


def test_find_mispricings_skips_markets_without_fair_value() -> None:
    markets = [_mkt("FED", 33, 69), _mkt("UNKNOWN", 50, 51)]
    opps = find_mispricings(markets, {"FED": 0.55})
    assert len(opps) == 1


def test_better_side_is_chosen() -> None:
    # Symmetric-ish book; fair value low should select NO.
    m = _mkt("Z", 40, 62)
    opp = mispricing(m, 0.15)
    assert opp is not None
    # NO win prob = 0.85, NO at 62c -> edge 0.23; YES edge negative.
    assert "buy NO" in opp.description
    assert opp.edge == pytest.approx(0.85 - 0.62, abs=1e-9)
    _ = Side.NO  # keep import meaningful
