from __future__ import annotations

import pytest

from edgehunt.feed import FakeFeed, LiveFeed, MarketFeed
from edgehunt.models import Market


def test_fakefeed_is_a_market_feed() -> None:
    assert isinstance(FakeFeed(), MarketFeed)


def test_fakefeed_deterministic() -> None:
    a = FakeFeed().fetch_markets()
    b = FakeFeed().fetch_markets()
    assert a == b
    assert len(a) == 7


def test_fakefeed_markets_are_valid() -> None:
    for m in FakeFeed().fetch_markets():
        assert 1 <= m.yes_ask <= 99
        assert 1 <= m.no_ask <= 99
        assert m.yes_ask >= m.yes_bid
        assert m.no_ask >= m.no_bid


def test_fakefeed_contains_cross_venue_pair() -> None:
    markets = FakeFeed().fetch_markets()
    keys = [m.join_key for m in markets]
    # The popular-vote event appears on two venues.
    assert keys.count("pres-popular-vote") == 2


def test_fakefeed_fair_values_keys_exist() -> None:
    feed = FakeFeed()
    tickers = {m.ticker for m in feed.fetch_markets()}
    for ticker in feed.fair_values():
        assert ticker in tickers


def test_livefeed_raises_without_fetcher() -> None:
    with pytest.raises(NotImplementedError):
        LiveFeed().fetch_markets()


def test_livefeed_uses_supplied_fetcher() -> None:
    sample = [
        Market(
            venue="kalshi",
            ticker="X",
            question="q",
            yes_bid=40,
            yes_ask=42,
            no_bid=56,
            no_ask=58,
        )
    ]
    feed = LiveFeed(lambda: sample, lambda: {"X": 0.5})
    assert feed.fetch_markets() == sample
    assert feed.fair_values() == {"X": 0.5}


def test_livefeed_default_fair_values_empty() -> None:
    feed = LiveFeed(lambda: [])
    assert feed.fair_values() == {}
