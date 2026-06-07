from __future__ import annotations

import pytest

from edgehunt.ev import (
    break_even_probability,
    edge,
    expected_value,
    implied_probability,
)
from edgehunt.fees import KalshiFeeModel, ZeroFeeModel
from edgehunt.models import Side


def test_implied_probability() -> None:
    assert implied_probability(60) == pytest.approx(0.60)
    assert implied_probability(1) == pytest.approx(0.01)
    assert implied_probability(99) == pytest.approx(0.99)


def test_implied_probability_out_of_range() -> None:
    with pytest.raises(ValueError):
        implied_probability(0)
    with pytest.raises(ValueError):
        implied_probability(100)


def test_expected_value_yes_no_fee() -> None:
    # p=0.60, buy YES at 50c, no fee: EV = 0.60 - 0.50 = 0.10.
    assert expected_value(0.60, 50, Side.YES, ZeroFeeModel()) == pytest.approx(0.10)


def test_expected_value_no_side_no_fee() -> None:
    # p=0.60 (YES), buy NO at 30c: win prob = 0.40, EV = 0.40 - 0.30 = 0.10.
    assert expected_value(0.60, 30, Side.NO, ZeroFeeModel()) == pytest.approx(0.10)


def test_expected_value_negative_when_overpaying() -> None:
    # p=0.40, buy YES at 50c: EV = 0.40 - 0.50 = -0.10.
    assert expected_value(0.40, 50, Side.YES, ZeroFeeModel()) == pytest.approx(-0.10)


def test_expected_value_includes_fee() -> None:
    # p=0.60, YES at 50c, Kalshi fee at 50c = 0.02 -> EV = 0.10 - 0.02 = 0.08.
    ev = expected_value(0.60, 50, Side.YES, KalshiFeeModel())
    assert ev == pytest.approx(0.08)


def test_expected_value_scales_with_count() -> None:
    ev = expected_value(0.60, 50, Side.YES, ZeroFeeModel(), count=10)
    assert ev == pytest.approx(1.00)


def test_break_even_yes_no_fee() -> None:
    # Break-even YES probability for YES at 40c with no fee is 0.40.
    assert break_even_probability(40, Side.YES, ZeroFeeModel()) == pytest.approx(0.40)


def test_break_even_no_side() -> None:
    # NO at 30c: break-even YES prob = 1 - 0.30 = 0.70.
    assert break_even_probability(30, Side.NO, ZeroFeeModel()) == pytest.approx(0.70)


def test_break_even_with_fee_is_higher() -> None:
    # YES at 50c with Kalshi fee 0.02 -> break-even 0.52.
    assert break_even_probability(50, Side.YES, KalshiFeeModel()) == pytest.approx(0.52)


def test_ev_zero_at_break_even() -> None:
    be = break_even_probability(50, Side.YES, KalshiFeeModel())
    assert expected_value(be, 50, Side.YES, KalshiFeeModel()) == pytest.approx(0.0, abs=1e-9)


def test_edge_is_probability_minus_price() -> None:
    assert edge(0.65, 50, Side.YES) == pytest.approx(0.15)
    assert edge(0.65, 50, Side.NO) == pytest.approx(0.35 - 0.50)


def test_expected_value_rejects_bad_probability() -> None:
    with pytest.raises(ValueError):
        expected_value(1.5, 50)
