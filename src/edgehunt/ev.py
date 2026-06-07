"""Expected-value and probability math for binary contracts.

The vocabulary:

- **Implied probability** -- the price of a YES contract *is* the market's
  estimate of the probability the event happens. A YES contract trading at 60c
  implies a 60% chance. So ``implied_probability(60) == 0.60``.

- **Expected value (EV)** -- given *your* estimate ``p`` of the true
  probability, buying a YES contract at price ``a`` (cents) pays $1 with
  probability ``p`` and $0 otherwise, costing ``a/100`` plus fees::

      EV = p * (1 - a/100) - (1 - p) * (a/100) - fee
         = p - a/100 - fee

  The clean ``p - price`` form is why edge is so easy to reason about: your
  per-contract edge before fees is simply *your probability minus the price*.

- **Break-even probability** -- the value of ``p`` that makes EV exactly zero.
  Below it the bet loses money in expectation; above it, it wins.
"""

from __future__ import annotations

from edgehunt.fees import FeeModel, ZeroFeeModel
from edgehunt.models import CENTS_PER_DOLLAR, Side


def implied_probability(price_cents: int) -> float:
    """Market-implied probability from a contract price in cents.

    Args:
        price_cents: Contract price, 1..99.

    Returns:
        Implied probability in (0, 1).
    """
    if not 1 <= price_cents <= 99:
        raise ValueError(f"price_cents must be in [1, 99], got {price_cents}")
    return price_cents / CENTS_PER_DOLLAR


def expected_value(
    edge_probability: float,
    price_cents: int,
    side: Side = Side.YES,
    fee: FeeModel | None = None,
    count: int = 1,
) -> float:
    """Expected profit in dollars of entering ``count`` contracts.

    For a YES position bought at ``a`` cents with true probability ``p``::

        EV = (p - a/100) * count - fees

    For a NO position bought at ``a`` cents, the payout happens with
    probability ``1 - p``, so::

        EV = ((1 - p) - a/100) * count - fees

    Args:
        edge_probability: *Your* estimate of the YES probability (0..1).
        price_cents: Entry price of the chosen ``side`` in cents.
        side: Which leg you are buying.
        fee: Fee model; defaults to zero-fee.
        count: Number of contracts.

    Returns:
        Expected profit in dollars (can be negative).
    """
    if not 0.0 <= edge_probability <= 1.0:
        raise ValueError("edge_probability must be in [0, 1]")
    if count < 0:
        raise ValueError("count must be non-negative")
    fee = fee or ZeroFeeModel()

    win_prob = edge_probability if side is Side.YES else 1.0 - edge_probability
    price = price_cents / CENTS_PER_DOLLAR
    gross = (win_prob - price) * count
    return gross - fee.trade_fee(price_cents, count)


def break_even_probability(
    price_cents: int,
    side: Side = Side.YES,
    fee: FeeModel | None = None,
) -> float:
    """The YES-probability at which a one-contract position breaks even.

    For a YES position the break-even is ``price + fee`` (as a fraction). For a
    NO position the payout leg is ``1 - p``, so the break-even YES probability
    is ``1 - (price + fee)``.

    Args:
        price_cents: Entry price in cents.
        side: Which leg you are buying.
        fee: Fee model; defaults to zero-fee.

    Returns:
        Break-even YES probability in (0, 1).
    """
    fee = fee or ZeroFeeModel()
    price = price_cents / CENTS_PER_DOLLAR
    fee_frac = fee.trade_fee(price_cents, 1)
    if side is Side.YES:
        return price + fee_frac
    return 1.0 - (price + fee_frac)


def edge(edge_probability: float, price_cents: int, side: Side = Side.YES) -> float:
    """Raw (pre-fee) edge in probability points for one contract.

    Positive means the bet has positive expectation before fees.
    """
    if not 0.0 <= edge_probability <= 1.0:
        raise ValueError("edge_probability must be in [0, 1]")
    win_prob = edge_probability if side is Side.YES else 1.0 - edge_probability
    return win_prob - price_cents / CENTS_PER_DOLLAR


__all__ = [
    "break_even_probability",
    "edge",
    "expected_value",
    "implied_probability",
]
