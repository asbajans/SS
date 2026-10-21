"""Billing catalog + credit math (offline)."""
from datetime import UTC, datetime

from app.billing_api import _period_end, _plan_by_price, _plan_catalog
from app.config import settings
from app.llm_gateway.usage import credit_debit
from app.plans import plan_limits
from app.runs_api import _validate_sim_config


def test_plan_catalog_shape():
    rows = {p["key"]: p for p in _plan_catalog()}
    assert set(rows) == {"free", "starter", "pro"}
    assert rows["free"]["token_budget"] == 1_000_000
    assert rows["starter"]["token_budget"] == 8_000_000
    assert rows["pro"]["token_budget"] == 25_000_000
    assert rows["free"]["price_id"] == ""


def test_checkout_flag_follows_stripe_config(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "stripe_price_starter", "price_starter")
    rows = {p["key"]: p for p in _plan_catalog()}
    assert rows["starter"]["checkout_enabled"] is False
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    rows = {p["key"]: p for p in _plan_catalog()}
    assert rows["starter"]["checkout_enabled"] is True


def test_price_mapping(monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_starter", "price_s")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_p")
    assert _plan_by_price("price_s")["key"] == "starter"
    assert _plan_by_price("price_p")["key"] == "pro"
    assert _plan_by_price("unknown") is None


def test_period_end_item_level():
    sub = {"items": {"data": [{"current_period_end": 1_800_000_000}]}}
    assert _period_end(sub) == datetime.fromtimestamp(1_800_000_000, UTC)
    sub = {"current_period_end": 1_700_000_000, "items": {"data": []}}
    assert _period_end(sub) == datetime.fromtimestamp(1_700_000_000, UTC)
    assert _period_end({}) is None


def test_plan_limits():
    assert plan_limits("free")["agents"] == 80
    assert plan_limits("starter")["agents"] == 150
    assert plan_limits("pro")["rounds"] == 80
    assert plan_limits("unknown")["plan"] == "free"


def test_sim_config_respects_plan():
    assert _validate_sim_config({"agents_n": 80, "rounds": 24}, "free") is None
    assert _validate_sim_config({"agents_n": 81, "rounds": 24}, "free") is not None
    assert _validate_sim_config({"agents_n": 150, "rounds": 40}, "free") is not None
    assert _validate_sim_config({"agents_n": 150, "rounds": 40}, "starter") is None
    assert _validate_sim_config({"agents_n": 300, "rounds": 80}, "pro") is None
    assert _validate_sim_config({"agents_n": 301, "rounds": 80}, "pro") is not None
    assert _validate_sim_config({}, "free", {"agents_n": 60, "rounds": 20}) is None
    assert _validate_sim_config({}, "free", {"agents_n": 100, "rounds": 20}) is not None


def test_credit_debit():
    assert credit_debit(900, 1100, 1000, 500) == 100
    assert credit_debit(1000, 1200, 1000, 50) == 50
    assert credit_debit(1100, 1200, 1000, 500) == 100
    assert credit_debit(900, 950, 1000, 500) == 0
    assert credit_debit(1000, 1200, 1000, 0) == 0
