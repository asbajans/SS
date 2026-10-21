"""Billing catalog + credit/free-trial math (offline)."""
from datetime import UTC, datetime, timedelta

from app.billing_api import _period_end
from app.llm_gateway.usage import credit_debit
from app.plans import DEFAULT_PLANS, free_access_expired, free_until
from app.runs_api import _validate_sim_config

FREE = {"plan": "free", "agents": 80, "rounds": 24}
STARTER = {"plan": "starter", "agents": 150, "rounds": 40}
PRO = {"plan": "pro", "agents": 300, "rounds": 80}


def test_default_plans_shape():
    rows = {p["key"]: p for p in DEFAULT_PLANS}
    assert set(rows) == {"free", "starter", "pro"}
    assert rows["free"]["token_budget"] == 1_000_000
    assert rows["starter"]["token_budget"] == 8_000_000
    assert rows["pro"]["token_budget"] == 25_000_000


def test_period_end_item_level():
    sub = {"items": {"data": [{"current_period_end": 1_800_000_000}]}}
    assert _period_end(sub) == datetime.fromtimestamp(1_800_000_000, UTC)
    sub = {"current_period_end": 1_700_000_000, "items": {"data": []}}
    assert _period_end(sub) == datetime.fromtimestamp(1_700_000_000, UTC)
    assert _period_end({}) is None


def test_sim_config_respects_plan():
    assert _validate_sim_config({"agents_n": 80, "rounds": 24}, FREE) is None
    assert _validate_sim_config({"agents_n": 81, "rounds": 24}, FREE) is not None
    assert _validate_sim_config({"agents_n": 150, "rounds": 40}, FREE) is not None
    assert _validate_sim_config({"agents_n": 150, "rounds": 40}, STARTER) is None
    assert _validate_sim_config({"agents_n": 300, "rounds": 80}, PRO) is None
    assert _validate_sim_config({"agents_n": 301, "rounds": 80}, PRO) is not None
    assert _validate_sim_config({}, FREE, {"agents_n": 60, "rounds": 20}) is None
    assert _validate_sim_config({}, FREE, {"agents_n": 100, "rounds": 20}) is not None


def test_free_trial_window():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    assert free_until(created, 0) is None
    assert free_until(created, 14) == created + timedelta(days=14)
    assert not free_access_expired(created, 14, created + timedelta(days=13, hours=23))
    assert free_access_expired(created, 14, created + timedelta(days=14))
    assert not free_access_expired(created, 0, created + timedelta(days=999))


def test_credit_debit():
    assert credit_debit(900, 1100, 1000, 500) == 100
    assert credit_debit(1000, 1200, 1000, 50) == 50
    assert credit_debit(1100, 1200, 1000, 500) == 100
    assert credit_debit(900, 950, 1000, 500) == 0
    assert credit_debit(1000, 1200, 1000, 0) == 0
