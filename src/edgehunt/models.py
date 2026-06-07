"""Core data models for edgehunt.

Prices are quoted in **cents** (integer 1..99) for a binary contract that pays
out **100 cents = $1** if it resolves YES, and 0 otherwise. This mirrors the
convention used by Kalshi and (after scaling) Polymarket.

A ``Market`` carries a two-sided order book for both the YES and NO legs:

- ``yes_bid`` / ``yes_ask`` -- best bid/ask for the YES contract.
- ``no_bid``  / ``no_ask``  -- best bid/ask for the NO contract.

On a well-formed binary book ``yes_ask + no_bid`` is roughly 100 and
``yes_bid + no_ask`` is roughly 100, but real venues drift from that -- which
is exactly where the edge lives.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

CENTS_PER_DOLLAR = 100


class Side(str, Enum):
    """Which leg of a binary contract a position is on."""

    YES = "YES"
    NO = "NO"


class OpportunityType(str, Enum):
    """Category of an edge surfaced by the scanner."""

    SINGLE_MARKET_ARB = "single_market_arb"
    CROSS_VENUE_ARB = "cross_venue_arb"
    MISPRICING = "mispricing"


class Market(BaseModel):
    """A single binary prediction-market contract on one venue.

    All four price fields are integer cents in ``[1, 99]``.
    """

    model_config = ConfigDict(frozen=True)

    venue: str = Field(..., description="Venue identifier, e.g. 'kalshi' or 'polymarket'.")
    ticker: str = Field(..., description="Venue-specific contract ticker.")
    question: str = Field(..., description="Human-readable market question.")
    yes_bid: int = Field(..., ge=1, le=99, description="Best bid for YES, in cents.")
    yes_ask: int = Field(..., ge=1, le=99, description="Best ask for YES, in cents.")
    no_bid: int = Field(..., ge=1, le=99, description="Best bid for NO, in cents.")
    no_ask: int = Field(..., ge=1, le=99, description="Best ask for NO, in cents.")
    volume: int = Field(0, ge=0, description="Traded contract volume (for liquidity ranking).")
    close_ts: int | None = Field(None, description="Unix timestamp the market closes, if known.")
    event_key: str | None = Field(
        None,
        description="Cross-venue join key: same event on different venues shares this key.",
    )

    @model_validator(mode="after")
    def _check_spreads(self) -> Market:
        if self.yes_ask < self.yes_bid:
            raise ValueError(f"yes_ask ({self.yes_ask}) < yes_bid ({self.yes_bid})")
        if self.no_ask < self.no_bid:
            raise ValueError(f"no_ask ({self.no_ask}) < no_bid ({self.no_bid})")
        return self

    @property
    def join_key(self) -> str:
        """Key used to match the same event across venues.

        Falls back to a normalised question string when no explicit
        ``event_key`` is provided.
        """
        if self.event_key:
            return self.event_key
        return self.question.strip().lower()

    @property
    def yes_mid(self) -> float:
        """Mid price of the YES contract in cents."""
        return (self.yes_bid + self.yes_ask) / 2

    @property
    def no_mid(self) -> float:
        """Mid price of the NO contract in cents."""
        return (self.no_bid + self.no_ask) / 2


class Opportunity(BaseModel):
    """A ranked edge produced by the scanner.

    Monetary fields are expressed in **dollars** for readability in the
    dashboard. ``score`` is the value the scanner sorts on (descending).
    """

    model_config = ConfigDict(frozen=True)

    kind: OpportunityType
    venue: str = Field(..., description="Venue(s) involved, e.g. 'kalshi' or 'kalshi/polymarket'.")
    question: str
    description: str = Field(..., description="One-line human-readable summary of the edge.")
    edge: float = Field(..., description="Edge in probability points (0..1) or arb margin (0..1).")
    ev_per_contract: float = Field(..., description="Expected profit per $1 contract, in dollars.")
    profit_per_dollar: float = Field(
        ...,
        description="Guaranteed/expected profit per $1 deployed at the recommended stake.",
    )
    stake: float = Field(..., ge=0.0, description="Recommended stake in dollars (Kelly-sized).")
    score: float = Field(..., description="Ranking score; higher is better.")

    @property
    def is_profitable(self) -> bool:
        """Whether the opportunity has positive expected/locked profit."""
        return self.profit_per_dollar > 0.0


__all__ = [
    "CENTS_PER_DOLLAR",
    "Market",
    "Opportunity",
    "OpportunityType",
    "Side",
]
