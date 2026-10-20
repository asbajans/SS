"""Billing catalog + credit math (offline)."""
from datetime import UTC, datetime

from app.billing_api import _period_end, _plan_by_price, _plan_catalog
from app.config import settings
from app.llm_gateway.usage import credit_debit


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


def test_credit_debit():
    assert credit_debit(900, 1100, 1000, 500) == 100
    assert credit_debit(1000, 1200, 1000, 50) == 50
    assert credit_debit(1100, 1200, 1000, 500) == 100
    assert credit_debit(900, 950, 1000, 500) == 0
    assert credit_debit(1000, 1200, 1000, 0) == 0
