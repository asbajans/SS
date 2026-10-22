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

from sqlalchemy import select
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

# --- event catalogue (shared with the GA4 setup script) ---

# (event_name, description, is_key_event)
EVENT_DEFINITIONS: list[tuple[str, str, bool]] = [
    ("sign_up", "Yeni hesap olusturuldu (google/epoosta ayrimli)", True),
    ("login", "Giris yapildi", False),
    ("checkout_start", "Odeme sayfasi acildi", False),
    ("purchase", "Odeme tamamlandi (paket satin alindi)", True),
    ("subscription_renew", "Periyodik abonelik yenilemesi", True),
    ("plan_change", "Plan degisikligi (yukseltme/indirim)", False),
]

# GA4'da "Key event" olarak isaretlenecek olaylar (donusumler)
KEY_EVENTS = [name for name, _, is_key in EVENT_DEFINITIONS if is_key]

# (param_name, description) -> GA4 event-scope custom dimension
CUSTOM_DIMENSIONS: list[tuple[str, str]] = [
    ("signup_method", "Uyelik yontemi: google | email"),
    ("method", "GA4 standart uyelik yontemi"),
    ("plan", "Satin alinan / aktif plan"),
    ("item_type", "subscription | credit_pack"),
    ("payment_type", "subscription | one_time"),
    ("item_name", "Satin alinan urun"),
    ("transaction_id", "Odeme islem kimligi"),
]

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


# --------------------------------------------------------------------------
# Server-side delivery (GA4 Measurement Protocol)
# --------------------------------------------------------------------------


async def dispatch_pending(db: AsyncSession, limit: int = 50) -> dict:
    """Send queued backend events to GA4 via the Measurement Protocol.

    Events are marked as delivered once GA4 accepts them. When no API secret
    is configured the events stay pending so the browser can deliver them
    with gtag.js instead.
    """
    from app.ga4 import SERVER_OWNED_EVENTS, client_id_for, send_batch
    from app.models import SeoSettings

    seo = await db.get(SeoSettings, 1)
    measurement_id = (seo.analytics_id if seo else "") or ""
    api_secret = (seo.ga4_api_secret if seo else "") or ""
    if not measurement_id or not api_secret:
        return {"skipped": True, "reason": "measurement_id/api_secret yok"}

    rows = (
        await db.scalars(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.delivered_at.is_(None))
            .order_by(AnalyticsEvent.created_at.asc())
            .limit(limit)
        )
    ).all()
    if not rows:
        return {"sent": 0}

    events = []
    for row in rows:
        if row.name not in SERVER_OWNED_EVENTS:
            # browser-owned events are delivered by the SPA
            continue
        params = dict(row.params or {})
        if row.value is not None:
            params.setdefault("value", float(row.value))
        if row.currency:
            params.setdefault("currency", row.currency)
        events.append(
            {
                "name": row.name,
                "params": params,
                "client_id": client_id_for(row.user_id),
            }
        )

    if not events:
        return {"sent": 0}

    result = await send_batch(measurement_id, api_secret, events)
    if not result.get("ok"):
        return result

    stamp = datetime.now(UTC)
    for row in rows:
        if row.name in SERVER_OWNED_EVENTS:
            row.delivered_at = stamp
    await db.commit()
    return {"sent": len(events), "status": result.get("status")}
