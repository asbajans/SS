"""Product analytics events (GA4).

Server-side facts (signup, Stripe purchase) are written to `analytics_events`
and drained by the SPA, which forwards them to GA4 via gtag. The SPA also
records client-side events directly.

Event contract (keep in sync with web/src/analytics.js):

    sign_up              params: signup_method (google|email), method, plan
    login                params: signup_method (google|email), method
    checkout_start       params: plan, item_type, value, currency
    purchase             params: transaction_id, plan, item_type, payment_type,
                               items, value, currency
    subscription_renew   params: plan, value, currency
    plan_change          params: plan, previous_plan, payment_type, value, currency
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalyticsEvent

# --- event names ---
SIGN_UP = "sign_up"
LOGIN = "login"
CHECKOUT_START = "checkout_start"
PURCHASE = "purchase"
SUBSCRIPTION_RENEW = "subscription_renew"
PLAN_CHANGE = "plan_change"

# --- signup methods ---
METHOD_GOOGLE = "google"
METHOD_EMAIL = "email"

# --- item types ---
ITEM_SUBSCRIPTION = "subscription"
ITEM_CREDIT_PACK = "credit_pack"

NAME_RE = re.compile(r"^[a-z0-9_]{1,64}$")


def normalize_name(name: str) -> str:
    """Lowercase snake_case event name; returns '' when unusable."""
    cleaned = re.sub(r"[^a-z0-9_]+", "_", (name or "").strip().lower()).strip("_")
    return cleaned if NAME_RE.match(cleaned) else ""


async def record(
    db: AsyncSession,
    name: str,
    *,
    user_id=None,
    params: dict | None = None,
    value: float | None = None,
    currency: str | None = None,
    source: str = "backend",
) -> AnalyticsEvent | None:
    """Queue an analytics event for delivery to GA4."""
    event_name = normalize_name(name)
    if not event_name:
        return None
    event = AnalyticsEvent(
        user_id=user_id,
        name=event_name,
        source=source,
        params=params or {},
        value=value,
        currency=(currency or "").upper() or None,
    )
    db.add(event)
    return event


def signup_params(method: str, plan: str = "free") -> dict:
    """Params for sign_up / login events."""
    return {
        "signup_method": method,
        "method": method,
        "plan": plan,
    }


def purchase_params(
    *,
    transaction_id: str,
    plan: str,
    item_type: str,
    payment_type: str,
    value: float | None,
    currency: str,
    item_name: str = "",
    items: list[dict] | None = None,
) -> dict:
    """GA4 compatible purchase params."""
    params = {
        "transaction_id": transaction_id,
        "plan": plan,
        "item_type": item_type,
        "payment_type": payment_type,
        "value": round(float(value or 0.0), 2),
        "currency": (currency or "USD").upper(),
    }
    if item_name:
        params["item_name"] = item_name
    if items:
        params["items"] = items
    return params


def serialize(event: AnalyticsEvent) -> dict:
    """Payload sent to the browser (value/currency merged into params)."""
    params = dict(event.params or {})
    if event.value is not None:
        params.setdefault("value", float(event.value))
    if event.currency:
        params.setdefault("currency", event.currency)
    return {
        "id": str(event.id),
        "name": event.name,
        "params": params,
        "value": float(event.value) if event.value is not None else None,
        "currency": event.currency,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def now() -> datetime:
    return datetime.now(UTC)
