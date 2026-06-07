"""edgehunt -- prediction-market edge & arbitrage engine.

A small, dependency-light analytics layer that scans prediction markets
(Kalshi / Polymarket style) and surfaces the *edge*: cross-venue arbitrage,
fee-adjusted expected value, Kelly position sizing, break-even win-rate and
fair-value mispricing.

This is an *analytics* library, not an execution wrapper. It never places an
order. Wire it to a real venue with the :class:`~edgehunt.feed.MarketFeed`
protocol, or run everything offline with the built-in
:class:`~edgehunt.feed.FakeFeed`.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
