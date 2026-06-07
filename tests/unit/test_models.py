from __future__ import annotations

import pytest
from pydantic import ValidationError

from edgehunt.models import Market, Opportunity, OpportunityType


def _market(**kw: object) -> Market:
    base = {
        "venue": "kalshi",
        "ticker": "T",
        "question": "Will X happen?",
        "yes_bid": 40,
        "yes_ask": 42,
        "no_bid": 56,
        "no_ask": 58,
    }
    base.update(kw)
    return Market(**base)  # type: ignore[arg-type]


def test_market_mids() -> None:
    m = _market()
    assert m.yes_mid == pytest.approx(41.0)
    assert m.no_mid == pytest.approx(57.0)


def test_market_join_key_uses_event_key() -> None:
    assert _market(event_key="abc").join_key == "abc"


def test_market_join_key_falls_back_to_question() -> None:
    assert _market(question="  Will X Happen?  ").join_key == "will x happen?"


def test_market_rejects_crossed_book() -> None:
    with pytest.raises(ValidationError):
        _market(yes_bid=50, yes_ask=40)


def test_market_rejects_out_of_range_price() -> None:
    with pytest.raises(ValidationError):
        _market(yes_ask=0)
    with pytest.raises(ValidationError):
        _market(no_ask=100)


def test_market_is_frozen() -> None:
    m = _market()
    with pytest.raises(ValidationError):
        m.yes_ask = 50  # type: ignore[misc]


def test_opportunity_is_profitable() -> None:
    opp = Opportunity(
        kind=OpportunityType.MISPRICING,
        venue="kalshi",
        question="q",
        description="d",
        edge=0.1,
        ev_per_contract=0.05,
        profit_per_dollar=0.1,
        stake=100.0,
        score=0.05,
    )
    assert opp.is_profitable

    loser = opp.model_copy(update={"profit_per_dollar": -0.1})
    assert not loser.is_profitable
