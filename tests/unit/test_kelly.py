from __future__ import annotations

import pytest

from edgehunt.kelly import fractional_kelly, kelly_fraction, stake
from edgehunt.models import Side


def test_kelly_fraction_known_value() -> None:
    # p=0.60, price 40c -> b=1.5, f=(0.6*1.5-0.4)/1.5 = 1/3.
    assert kelly_fraction(0.60, 40, Side.YES) == pytest.approx(1.0 / 3.0)


def test_kelly_fraction_fair_priced_is_zero() -> None:
    # When your probability equals the price, edge is zero -> no bet.
    assert kelly_fraction(0.50, 50, Side.YES) == pytest.approx(0.0)


def test_kelly_no_bet_when_no_edge() -> None:
    # p=0.40, price 50c: negative edge -> clamp to 0, never negative.
    assert kelly_fraction(0.40, 50, Side.YES) == 0.0


def test_kelly_fraction_second_known_value() -> None:
    # p=0.70, price 50c -> b=1.0, f = (0.7*1 - 0.3)/1 = 0.40.
    assert kelly_fraction(0.70, 50, Side.YES) == pytest.approx(0.40)


def test_kelly_no_side() -> None:
    # YES prob 0.30 -> NO win prob 0.70; NO at 50c -> b=1, f=0.40.
    assert kelly_fraction(0.30, 50, Side.NO) == pytest.approx(0.40)


def test_kelly_full_at_certainty() -> None:
    # p=1.0 at any price < 1 -> full Kelly is 1.0 (bet whole bankroll).
    assert kelly_fraction(1.0, 50, Side.YES) == pytest.approx(1.0)


def test_half_kelly_is_half_of_full() -> None:
    full = kelly_fraction(0.70, 50, Side.YES)
    half = fractional_kelly(0.70, 50, 0.5, Side.YES)
    assert half == pytest.approx(full / 2.0)


def test_fractional_kelly_capped_at_one() -> None:
    # Aggressive multiplier should never exceed 100% of bankroll.
    assert fractional_kelly(1.0, 50, fraction=5.0) == pytest.approx(1.0)


def test_stake_from_bankroll() -> None:
    # full Kelly 1/3 of $900 at half-Kelly = 900 * (1/3) * 0.5 = 150.
    assert stake(900.0, 0.60, 40, fraction=0.5) == pytest.approx(150.0)


def test_stake_zero_when_no_edge() -> None:
    assert stake(1000.0, 0.40, 50) == 0.0


def test_kelly_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        kelly_fraction(1.2, 50)
    with pytest.raises(ValueError):
        kelly_fraction(0.5, 0)
    with pytest.raises(ValueError):
        fractional_kelly(0.6, 40, fraction=-1.0)
    with pytest.raises(ValueError):
        stake(-100.0, 0.6, 40)
