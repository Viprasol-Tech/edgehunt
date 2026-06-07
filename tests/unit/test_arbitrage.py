from __future__ import annotations

import pytest

from edgehunt.arbitrage import (
    cross_venue_arbitrage,
    find_cross_venue_arbs,
    single_market_arbitrage,
)
from edgehunt.fees import ZeroFeeModel
from edgehunt.models import Market, OpportunityType


def _mkt(venue: str, ya: int, na: int, key: str, ticker: str = "T") -> Market:
    return Market(
        venue=venue,
        ticker=ticker,
        question="q",
        yes_bid=max(1, ya - 2),
        yes_ask=ya,
        no_bid=max(1, na - 2),
        no_ask=na,
        event_key=key,
    )


def test_single_market_arb_detected_after_fees() -> None:
    # YES 45 + NO 48 = 93c; Kalshi fees 0.02+0.02=0.04 -> profit 0.03.
    m = _mkt("kalshi", 45, 48, "k1")
    opp = single_market_arbitrage(m)
    assert opp is not None
    assert opp.kind is OpportunityType.SINGLE_MARKET_ARB
    assert opp.edge == pytest.approx(0.03)
    assert opp.is_profitable


def test_single_market_no_arb_when_sum_ge_100() -> None:
    m = _mkt("kalshi", 50, 51, "k2")
    assert single_market_arbitrage(m) is None


def test_single_market_arb_killed_by_fees() -> None:
    # YES 47 + NO 50 = 97c but Kalshi fees 0.04 -> profit -0.01 -> None.
    m = _mkt("kalshi", 47, 50, "k3")
    assert single_market_arbitrage(m) is None


def test_single_market_arb_with_zero_fee_just_needs_sum_below_100() -> None:
    m = _mkt("kalshi", 47, 50, "k4")
    opp = single_market_arbitrage(m, fee=ZeroFeeModel())
    assert opp is not None
    assert opp.edge == pytest.approx(0.03)


def test_cross_venue_arb_picks_correct_direction() -> None:
    # YES cheap on kalshi (41), NO cheap on polymarket (43).
    k = _mkt("kalshi", 41, 60, "evt", "K")
    p = _mkt("polymarket", 58, 43, "evt", "P")
    opp = cross_venue_arbitrage(k, p)
    assert opp is not None
    assert opp.kind is OpportunityType.CROSS_VENUE_ARB
    # Direction: buy YES on kalshi, NO on polymarket.
    assert "YES@41c on kalshi" in opp.description
    assert "NO@43c on polymarket" in opp.description
    assert opp.edge > 0
    # 1 - 0.84 - (kalshi fee@41 + poly fee@43) ~= 0.131.
    assert opp.edge == pytest.approx(0.1314, abs=1e-3)


def test_cross_venue_no_arb_when_efficient() -> None:
    k = _mkt("kalshi", 50, 51, "evt2", "K")
    p = _mkt("polymarket", 50, 51, "evt2", "P")
    assert cross_venue_arbitrage(k, p) is None


def test_cross_venue_rejects_mismatched_events() -> None:
    k = _mkt("kalshi", 41, 60, "a", "K")
    p = _mkt("polymarket", 58, 43, "b", "P")
    with pytest.raises(ValueError):
        cross_venue_arbitrage(k, p)


def test_find_cross_venue_arbs_groups_and_ranks() -> None:
    markets = [
        _mkt("kalshi", 41, 60, "evt", "K"),
        _mkt("polymarket", 58, 43, "evt", "P"),
        _mkt("kalshi", 50, 51, "other", "K2"),  # no pair
    ]
    arbs = find_cross_venue_arbs(markets)
    assert len(arbs) == 1
    assert arbs[0].edge > 0


def test_find_cross_venue_skips_same_venue_pairs() -> None:
    markets = [
        _mkt("kalshi", 41, 43, "evt", "K1"),
        _mkt("kalshi", 41, 43, "evt", "K2"),
    ]
    assert find_cross_venue_arbs(markets) == []
