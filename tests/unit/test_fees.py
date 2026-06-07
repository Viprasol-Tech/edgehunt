from __future__ import annotations

import math

import pytest

from edgehunt.fees import (
    KalshiFeeModel,
    PercentFeeModel,
    ZeroFeeModel,
    fee_for_venue,
    net_cost,
)


def test_kalshi_fee_peaks_at_50c() -> None:
    model = KalshiFeeModel()
    # ceil(0.07 * 0.5 * 0.5 * 100) = ceil(1.75) = 2 cents.
    assert model.trade_fee(50, 1) == pytest.approx(0.02)


def test_kalshi_fee_matches_formula_for_various_prices() -> None:
    model = KalshiFeeModel()
    for price in (10, 25, 33, 47, 60, 90):
        p = price / 100
        expected = math.ceil(0.07 * 1 * p * (1 - p) * 100) / 100
        assert model.trade_fee(price, 1) == pytest.approx(expected)


def test_kalshi_fee_is_tiny_near_extremes() -> None:
    model = KalshiFeeModel()
    # ceil(0.07 * 0.05 * 0.95 * 100) = ceil(0.3325) = 1 cent.
    assert model.trade_fee(5, 1) == pytest.approx(0.01)


def test_kalshi_fee_scales_with_count() -> None:
    model = KalshiFeeModel()
    # ceil(0.07 * 100 * 0.5 * 0.5 * 100) = ceil(175.0) = 175 cents = $1.75.
    # (The model rounds away binary-float noise so 175.0 stays 175, not 176.)
    assert model.trade_fee(50, 100) == pytest.approx(1.75)


def test_kalshi_fee_zero_count_is_zero() -> None:
    assert KalshiFeeModel().trade_fee(50, 0) == 0.0


def test_percent_fee_is_two_percent_of_notional() -> None:
    model = PercentFeeModel()  # 2%
    # notional = 0.60 * 10 = 6.00; fee = 0.12.
    assert model.trade_fee(60, 10) == pytest.approx(0.12)


def test_percent_fee_custom_rate() -> None:
    model = PercentFeeModel(rate=0.05)
    assert model.trade_fee(40, 1) == pytest.approx(0.05 * 0.40)


def test_zero_fee_model() -> None:
    assert ZeroFeeModel().trade_fee(50, 100) == 0.0


def test_fee_for_known_and_unknown_venues() -> None:
    assert isinstance(fee_for_venue("kalshi"), KalshiFeeModel)
    assert isinstance(fee_for_venue("polymarket"), PercentFeeModel)
    assert isinstance(fee_for_venue("nonexistent"), ZeroFeeModel)


def test_fee_rejects_out_of_range_price() -> None:
    with pytest.raises(ValueError):
        KalshiFeeModel().trade_fee(0, 1)
    with pytest.raises(ValueError):
        PercentFeeModel().trade_fee(100, 1)


def test_net_cost_adds_notional_and_fee() -> None:
    fee = KalshiFeeModel()
    # notional = 0.50 * 1 = 0.50, fee = 0.02 -> 0.52.
    assert net_cost(50, 1, fee) == pytest.approx(0.52)
