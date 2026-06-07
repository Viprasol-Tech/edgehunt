"""Per-venue fee models.

Two real-world styles are supported:

**Kalshi style (per-contract, price-dependent).**
    Kalshi charges a trading fee that is largest near a 50c price and shrinks
    toward the extremes. Their published formula is::

        fee = ceil( base_rate * C * P * (1 - P) )   [in cents, per fill]

    where ``C`` is the contract count, ``P`` is the execution price as a
    fraction of $1, and ``base_rate`` is 0.07 for the standard maker/taker
    schedule (7%). We model this with :class:`KalshiFeeModel`. Because the fee
    depends on ``P*(1-P)`` it peaks at P=0.5 and is tiny near P=0 or P=1.

**Polymarket style (flat percentage of proceeds).**
    Polymarket-style venues take a flat percentage of net proceeds. We model
    this with :class:`PercentFeeModel` (default 2%).

All fee models return fees in **dollars** so they compose cleanly with the EV
and arbitrage math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from edgehunt.models import CENTS_PER_DOLLAR


@runtime_checkable
class FeeModel(Protocol):
    """A venue fee model.

    ``price_cents`` is the execution price of the contract (1..99). ``count``
    is the number of contracts. The return value is the fee in **dollars**.
    """

    def trade_fee(self, price_cents: int, count: int = 1) -> float:
        """Fee charged to *enter* a position, in dollars."""
        ...


@dataclass(frozen=True)
class KalshiFeeModel:
    """Kalshi-style per-contract fee: ``ceil(base_rate * C * P * (1-P))`` cents.

    Args:
        base_rate: Fee coefficient (default 0.07 == 7%, Kalshi's standard tier).
    """

    base_rate: float = 0.07

    def trade_fee(self, price_cents: int, count: int = 1) -> float:
        if not 1 <= price_cents <= 99:
            raise ValueError(f"price_cents must be in [1, 99], got {price_cents}")
        if count < 0:
            raise ValueError("count must be non-negative")
        if count == 0:
            return 0.0
        p = price_cents / CENTS_PER_DOLLAR
        raw_cents = self.base_rate * count * p * (1.0 - p) * CENTS_PER_DOLLAR
        # Round to a tiny tolerance first so exact integers (e.g. 175.0 stored
        # as 175.0000000002 in binary float) do not spuriously round up.
        fee_cents = math.ceil(round(raw_cents, 9))
        return fee_cents / CENTS_PER_DOLLAR


@dataclass(frozen=True)
class PercentFeeModel:
    """Polymarket-style flat percentage fee on the notional traded.

    Args:
        rate: Fraction of notional taken as fee (default 0.02 == 2%).
    """

    rate: float = 0.02

    def trade_fee(self, price_cents: int, count: int = 1) -> float:
        if not 1 <= price_cents <= 99:
            raise ValueError(f"price_cents must be in [1, 99], got {price_cents}")
        if count < 0:
            raise ValueError("count must be non-negative")
        notional = (price_cents / CENTS_PER_DOLLAR) * count
        return self.rate * notional


@dataclass(frozen=True)
class ZeroFeeModel:
    """A no-fee venue, useful for tests and theoretical comparisons."""

    def trade_fee(self, price_cents: int, count: int = 1) -> float:
        if not 1 <= price_cents <= 99:
            raise ValueError(f"price_cents must be in [1, 99], got {price_cents}")
        return 0.0


# Registry of named, ready-to-use fee models keyed by venue id.
DEFAULT_FEES: dict[str, FeeModel] = {
    "kalshi": KalshiFeeModel(),
    "polymarket": PercentFeeModel(),
}


def fee_for_venue(venue: str) -> FeeModel:
    """Return the default fee model for ``venue`` (zero-fee if unknown)."""
    return DEFAULT_FEES.get(venue.lower(), ZeroFeeModel())


def net_cost(price_cents: int, count: int, fee: FeeModel) -> float:
    """Total cost in dollars to enter a position: notional + entry fee."""
    notional = (price_cents / CENTS_PER_DOLLAR) * count
    return notional + fee.trade_fee(price_cents, count)


__all__ = [
    "DEFAULT_FEES",
    "FeeModel",
    "KalshiFeeModel",
    "PercentFeeModel",
    "ZeroFeeModel",
    "fee_for_venue",
    "net_cost",
]
