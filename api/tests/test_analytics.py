"""Product analytics events: naming, params and serialization (F11)."""
from datetime import UTC, datetime

from app.analytics import (
    ITEM_CREDIT_PACK,
    ITEM_SUBSCRIPTION,
    METHOD_EMAIL,
    METHOD_GOOGLE,
    PURCHASE,
    SIGN_UP,
    normalize_name,
    purchase_params,
    signup_params,
)


def test_normalize_name():
    assert normalize_name("Sign Up") == "sign_up"
    assert normalize_name("purchase-flow") == "purchase_flow"
    assert normalize_name("  plan_change  ") == "plan_change"
    assert normalize_name("") == ""
    assert normalize_name("!!!") == ""


def test_signup_params_separate_methods():
    google = signup_params(METHOD_GOOGLE, "free")
    email = signup_params(METHOD_EMAIL, "free")
    assert google["signup_method"] == "google"
    assert email["signup_method"] == "email"
    assert google["method"] == "google"
    assert google != email


def test_purchase_params_contain_amount_and_items():
    params = purchase_params(
        transaction_id="cs_123",
        plan="starter",
        item_type=ITEM_SUBSCRIPTION,
        payment_type="subscription",
        value=29.0,
        currency="usd",
        item_name="plan_starter",
        items=[{"item_id": "starter", "price": 29.0, "quantity": 1}],
    )
    assert params["transaction_id"] == "cs_123"
    assert params["value"] == 29.0
    assert params["currency"] == "USD"
    assert params["plan"] == "starter"
    assert params["item_type"] == ITEM_SUBSCRIPTION
    assert params["items"][0]["item_id"] == "starter"


def test_credit_pack_item_type():
    params = purchase_params(
        transaction_id="cs_456",
        plan="credit_5m",
        item_type=ITEM_CREDIT_PACK,
        payment_type="one_time",
        value=19.0,
        currency="USD",
    )
    assert params["payment_type"] == "one_time"
    assert params["item_type"] == ITEM_CREDIT_PACK


def test_serialize_merges_value_and_currency():
    from app.models import AnalyticsEvent

    event = AnalyticsEvent(
        id="11111111-1111-1111-1111-111111111111",
        name=PURCHASE,
        source="backend",
        params={"plan": "pro"},
        value=99.0,
        currency="USD",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    from app.analytics import serialize

    out = serialize(event)
    assert out["name"] == "purchase"
    assert out["params"]["plan"] == "pro"
    assert out["params"]["value"] == 99.0
    assert out["params"]["currency"] == "USD"
    assert out["value"] == 99.0


def test_event_names_are_stable():
    assert SIGN_UP == "sign_up"
    assert PURCHASE == "purchase"
