"""GA4 Measurement Protocol + Google API yardimcilari (F11)."""
from app.ga4 import (
    COLLECT_URL,
    DEBUG_URL,
    SERVER_OWNED_EVENTS,
    build_payload,
    client_id_for,
)
from app.google import PROVIDERS, SCOPES, GoogleCredentials


def test_client_id_is_stable_and_pseudonymous():
    a = client_id_for("11111111-1111-1111-1111-111111111111")
    b = client_id_for("11111111-1111-1111-1111-111111111111")
    c = client_id_for("22222222-2222-2222-2222-222222222222")
    assert a == b
    assert a != c
    assert a.startswith("ss.")
    assert "1111" not in a


def test_build_payload_shape():
    payload = build_payload("G-ABC12345", "secret", "purchase", {"value": 29.0, "currency": "USD"}, "ss.x")
    assert payload["measurement_id"] == "G-ABC12345"
    assert payload["api_secret"] == "secret"
    assert payload["client_id"] == "ss.x"
    event = payload["events"][0]
    assert event["name"] == "purchase"
    assert event["params"]["value"] == 29.0
    assert event["params"]["currency"] == "USD"


def test_build_payload_drops_none_params():
    payload = build_payload("G-1", "s", "login", {"a": None, "b": 1}, "ss.x")
    assert payload["events"][0]["params"] == {"b": 1}


def test_server_owned_events_cover_conversions():
    for name in ("sign_up", "purchase", "subscription_renew", "plan_change"):
        assert name in SERVER_OWNED_EVENTS
    # engagement events stay in the browser
    assert "select_plan" not in SERVER_OWNED_EVENTS


def test_collect_urls():
    assert COLLECT_URL.endswith("/mp/collect")
    assert DEBUG_URL.endswith("/debug/mp/collect")


def test_providers_and_scopes():
    assert "ga4" in PROVIDERS
    assert "search_console" in PROVIDERS
    assert "google_ads" in PROVIDERS
    assert "tag_manager" in PROVIDERS
    for provider in PROVIDERS:
        assert SCOPES[provider]


def test_credentials_is_complete():
    cred = GoogleCredentials(provider="ga4")
    assert not cred.is_complete
    cred.client_id = "id"
    cred.client_secret = "secret"
    cred.refresh_token = "refresh"
    assert cred.is_complete
    assert cred.get("property_id", "") == ""
    assert cred.get("property_id", "x") == "x"
