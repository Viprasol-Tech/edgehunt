"""Market feeds.

``edgehunt`` reads prices through a small :class:`MarketFeed` protocol so the
analytics never care where the data comes from. Two implementations ship:

- :class:`FakeFeed` -- a *deterministic* set of realistic synthetic markets,
  including a single-market arb, a cross-venue arb, and several mispricings.
  This is what ``edgehunt scan`` uses by default, so the demo and the entire
  test suite run with **no network and no API keys**.

- :class:`LiveFeed` -- a documented stub showing exactly where to plug a real
  Kalshi / Polymarket HTTP client. It deliberately raises until you supply a
  fetch callback, so importing it can never make a network call by accident.

To wire a real venue, implement ``fetch_markets()`` returning a list of
:class:`~edgehunt.models.Market` and pass it anywhere a ``MarketFeed`` is
accepted (the scanner, the CLI). Nothing else changes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from edgehunt.models import Market


@runtime_checkable
class MarketFeed(Protocol):
    """Anything that can produce a snapshot of markets."""

    def fetch_markets(self) -> list[Market]:
        """Return the current set of markets."""
        ...

    def fair_values(self) -> dict[str, float]:
        """Optional model probabilities keyed by ``Market.ticker``.

        Return an empty mapping if you have no fair-value model; the scanner
        then only reports arbitrage.
        """
        ...


class FakeFeed:
    """Deterministic synthetic markets for offline demos and tests.

    The data is fixed (no randomness) so output is byte-for-byte reproducible.
    It is hand-crafted to contain at least one of every edge type:

    - ``KXBTC-25`` has YES_ask 45c + NO_ask 48c = 93c -> single-market arb.
    - ``ELECTION-POP`` exists on both Kalshi and Polymarket with a price gap
      -> cross-venue arb.
    - Several markets carry a fair value that diverges from price -> mispricing.
    """

    def fetch_markets(self) -> list[Market]:
        return [
            # --- Single-market arbitrage: YES 47 + NO 50 = 97c < 100c. ---
            Market(
                venue="kalshi",
                ticker="KXBTC-25",
                question="Will BTC close above $100k on Dec 31?",
                yes_bid=43,
                yes_ask=45,
                no_bid=46,
                no_ask=48,
                volume=18250,
                event_key="btc-100k-dec31",
            ),
            # --- Cross-venue arbitrage pair: same event, both venues. ---
            Market(
                venue="kalshi",
                ticker="PRES-POP-K",
                question="Will the incumbent win the popular vote?",
                yes_bid=38,
                yes_ask=41,
                no_bid=57,
                no_ask=60,
                volume=92100,
                event_key="pres-popular-vote",
            ),
            Market(
                venue="polymarket",
                ticker="PRES-POP-P",
                question="Will the incumbent win the popular vote?",
                yes_bid=55,
                yes_ask=58,
                no_bid=40,
                no_ask=43,
                volume=140300,
                event_key="pres-popular-vote",
            ),
            # --- Mispricings (fair value diverges from price). ---
            Market(
                venue="kalshi",
                ticker="FED-CUT-MAR",
                question="Will the Fed cut rates in March?",
                yes_bid=30,
                yes_ask=33,
                no_bid=66,
                no_ask=69,
                volume=54200,
                event_key="fed-cut-march",
            ),
            Market(
                venue="polymarket",
                ticker="OSCAR-BP",
                question="Will 'The Brutalist' win Best Picture?",
                yes_bid=20,
                yes_ask=22,
                no_bid=77,
                no_ask=79,
                volume=31750,
                event_key="oscar-best-picture",
            ),
            Market(
                venue="kalshi",
                ticker="GDP-Q2-3",
                question="Will Q2 GDP growth exceed 3%?",
                yes_bid=61,
                yes_ask=64,
                no_bid=35,
                no_ask=38,
                volume=21600,
                event_key="gdp-q2-3pct",
            ),
            # --- Efficiently priced (no edge): should NOT surface. ---
            Market(
                venue="kalshi",
                ticker="RAIN-NYC",
                question="Will it rain in NYC tomorrow?",
                yes_bid=49,
                yes_ask=51,
                no_bid=49,
                no_ask=51,
                volume=4100,
                event_key="rain-nyc",
            ),
        ]

    def fair_values(self) -> dict[str, float]:
        """Model probabilities. Chosen so a few clear edges exist."""
        return {
            "FED-CUT-MAR": 0.55,  # fair 55% vs YES 33c -> strong YES edge
            "OSCAR-BP": 0.10,  # fair 10% vs YES 22c -> buy NO (cheap)
            "GDP-Q2-3": 0.66,  # fair 66% vs YES 64c -> small YES edge
            "RAIN-NYC": 0.50,  # fair 50% vs 51c -> no edge after fees
        }


class LiveFeed:
    """Stub adapter for a real venue. No network until you supply a fetcher.

    Example::

        import httpx
        from edgehunt.models import Market

        def kalshi_fetch() -> list[Market]:
            resp = httpx.get("https://api.elections.kalshi.com/...").json()
            return [
                Market(
                    venue="kalshi",
                    ticker=row["ticker"],
                    question=row["title"],
                    yes_bid=row["yes_bid"],
                    yes_ask=row["yes_ask"],
                    no_bid=row["no_bid"],
                    no_ask=row["no_ask"],
                    volume=row["volume"],
                )
                for row in resp["markets"]
            ]

        feed = LiveFeed(kalshi_fetch)
        scanner = Scanner(feed)
    """

    def __init__(
        self,
        fetcher: Callable[[], list[Market]] | None = None,
        fair_value_fn: Callable[[], dict[str, float]] | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._fair_value_fn = fair_value_fn

    def fetch_markets(self) -> list[Market]:
        if self._fetcher is None:
            raise NotImplementedError(
                "LiveFeed has no fetcher. Pass a callable returning list[Market], "
                "e.g. LiveFeed(my_kalshi_fetch). See the docstring for an example."
            )
        return self._fetcher()

    def fair_values(self) -> dict[str, float]:
        if self._fair_value_fn is None:
            return {}
        return self._fair_value_fn()


__all__ = ["FakeFeed", "LiveFeed", "MarketFeed"]
