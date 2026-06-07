"""Kelly criterion position sizing for binary prediction-market contracts.

The Kelly criterion maximises the long-run growth rate of a bankroll. For a
binary bet with win probability ``p`` and net odds ``b`` (profit per unit
staked on a win), the optimal fraction of bankroll to stake is::

    f* = (p * b - (1 - p)) / b
       = p - (1 - p) / b

For a binary contract priced at ``a`` (a fraction of $1), buying YES costs
``a`` and pays ``1`` on a win, so the net profit per unit *staked* is::

    b = (1 - a) / a

i.e. you risk ``a`` to make ``1 - a``. Substituting gives a clean closed form
in terms of the contract price. A contract trading at 40c with a true 60%
probability has ``b = 0.6/0.4 = 1.5`` and ``f* = (0.6*1.5 - 0.4)/1.5 = 0.333``.

When ``f*`` is negative the bet has no edge and the correct stake is **zero** --
never bet a contract whose price exceeds your probability. Most practitioners
use *fractional* Kelly (e.g. half-Kelly) to cut variance; this module supports
an arbitrary ``fraction`` multiplier.
"""

from __future__ import annotations

from edgehunt.models import CENTS_PER_DOLLAR, Side


def kelly_fraction(
    win_probability: float,
    price_cents: int,
    side: Side = Side.YES,
) -> float:
    """Full-Kelly fraction of bankroll for a binary contract.

    Args:
        win_probability: Your estimate of the YES probability (0..1).
        price_cents: Entry price of the chosen ``side`` in cents (1..99).
        side: Which leg you are buying.

    Returns:
        Optimal bankroll fraction in ``[0, 1]``. Returns ``0.0`` when the bet
        has no positive edge (never goes negative -- you simply do not bet).
    """
    if not 0.0 <= win_probability <= 1.0:
        raise ValueError("win_probability must be in [0, 1]")
    if not 1 <= price_cents <= 99:
        raise ValueError(f"price_cents must be in [1, 99], got {price_cents}")

    p = win_probability if side is Side.YES else 1.0 - win_probability
    price = price_cents / CENTS_PER_DOLLAR
    # Net odds: risk `price` to win `1 - price`.
    b = (1.0 - price) / price
    f = (p * b - (1.0 - p)) / b
    return max(0.0, f)


def fractional_kelly(
    win_probability: float,
    price_cents: int,
    fraction: float = 0.5,
    side: Side = Side.YES,
) -> float:
    """Scaled Kelly fraction (``fraction`` * full Kelly).

    Args:
        win_probability: Your estimate of the YES probability.
        price_cents: Entry price in cents.
        fraction: Kelly multiplier (0.5 == half-Kelly, the common default).
        side: Which leg you are buying.

    Returns:
        Bankroll fraction in ``[0, 1]``.
    """
    if fraction < 0.0:
        raise ValueError("fraction must be non-negative")
    return min(1.0, fraction * kelly_fraction(win_probability, price_cents, side))


def stake(
    bankroll: float,
    win_probability: float,
    price_cents: int,
    fraction: float = 0.5,
    side: Side = Side.YES,
) -> float:
    """Recommended stake in dollars from a bankroll using fractional Kelly.

    Args:
        bankroll: Total bankroll in dollars.
        win_probability: Your estimate of the YES probability.
        price_cents: Entry price in cents.
        fraction: Kelly multiplier (default half-Kelly).
        side: Which leg you are buying.

    Returns:
        Dollar stake (>= 0).
    """
    if bankroll < 0.0:
        raise ValueError("bankroll must be non-negative")
    return bankroll * fractional_kelly(win_probability, price_cents, fraction, side)


__all__ = [
    "fractional_kelly",
    "kelly_fraction",
    "stake",
]
