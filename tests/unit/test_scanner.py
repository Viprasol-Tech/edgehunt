from __future__ import annotations

from itertools import pairwise

from edgehunt.dashboard import build_table
from edgehunt.feed import FakeFeed
from edgehunt.models import OpportunityType
from edgehunt.scanner import Scanner


def test_scanner_finds_opportunities() -> None:
    scanner = Scanner(FakeFeed(), bankroll=1000.0, kelly_fraction=0.5)
    opps = scanner.scan()
    assert len(opps) >= 4
    kinds = {o.kind for o in opps}
    assert OpportunityType.SINGLE_MARKET_ARB in kinds
    assert OpportunityType.CROSS_VENUE_ARB in kinds
    assert OpportunityType.MISPRICING in kinds


def test_scanner_ranked_descending() -> None:
    opps = Scanner(FakeFeed()).scan()
    scores = [(o.kind, o.score) for o in opps]
    # Verify the merged board is sorted by (precedence, score) descending.
    for a, b in pairwise(scores):
        pa = 2 if a[0] is not OpportunityType.MISPRICING else 1
        pb = 2 if b[0] is not OpportunityType.MISPRICING else 1
        assert (pa, a[1]) >= (pb, b[1])


def test_scanner_arbs_rank_above_mispricings() -> None:
    opps = Scanner(FakeFeed()).scan()
    arb_indices = [i for i, o in enumerate(opps) if o.kind is not OpportunityType.MISPRICING]
    misprice_indices = [i for i, o in enumerate(opps) if o.kind is OpportunityType.MISPRICING]
    if arb_indices and misprice_indices:
        assert max(arb_indices) < min(misprice_indices)


def test_scanner_all_opportunities_profitable() -> None:
    for o in Scanner(FakeFeed()).scan():
        assert o.is_profitable


def test_scanner_best_returns_top() -> None:
    scanner = Scanner(FakeFeed())
    best = scanner.best()
    assert best is not None
    assert best == scanner.scan()[0]


def test_min_edge_reduces_results() -> None:
    base = Scanner(FakeFeed(), min_edge=0.0).scan()
    strict = Scanner(FakeFeed(), min_edge=0.10).scan()
    assert len(strict) <= len(base)


def test_efficient_market_not_surfaced() -> None:
    # RAIN-NYC (50/50 fair, 51c book) must never appear.
    opps = Scanner(FakeFeed()).scan()
    assert all("rain" not in o.question.lower() for o in opps)


def test_scanner_stake_scales_with_bankroll() -> None:
    small = Scanner(FakeFeed(), bankroll=100.0).scan()
    large = Scanner(FakeFeed(), bankroll=10000.0).scan()
    # The top arb stake is bankroll * kelly_fraction.
    assert large[0].stake > small[0].stake


def test_dashboard_table_builds() -> None:
    opps = Scanner(FakeFeed()).scan()
    table = build_table(opps, 1000.0)
    assert table.row_count == len(opps)


def test_dashboard_handles_empty() -> None:
    table = build_table([], 1000.0)
    assert table.row_count == 1
