"""GA4 Measurement Protocol — sunucu taraflı olay gönderimi.

Tarayıcıdaki gtag.js yerine sunucudan göndermek:
  - reklam engelleyicilerden / CSP'den etkilenmez
  - kullanici sekmeyi kapatirsa olay yine kaydedilir
  - Stripe webhook gibi sunucu olaylarini da ayni kanala alir

Gereken iki deger:
  - measurement_id : GA4 property ID (G-XXXXXXXXXX)
  - api_secret     : GA4 Admin > Property Settings > Data Streams > Web > "API secret"

Dogrulama icin debug ucu kullanilir; GA4 gonderim ayrintilarini dondurur.
"""
from __future__ import annotations

import hashlib

import httpx

COLLECT_URL = "https://www.google-analytics.com/mp/collect"
DEBUG_URL = "https://www.google-analytics.com/debug/mp/collect"

# Bu olaylar sunucudan gonderilir; tarayiciya gonderilmez (cift sayim olmaz).
SERVER_OWNED_EVENTS = {
    "sign_up",
    "login",
    "purchase",
    "subscription_renew",
    "plan_change",
    "checkout_start",
}


def client_id_for(user_id) -> str:
    """Stable pseudonymous client id derived from the user id."""
    raw = str(user_id or "anonymous")
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"ss.{digest}"


def build_payload(
    measurement_id: str,
    api_secret: str,
    name: str,
    params: dict | None = None,
    client_id: str = "ss.anonymous",
    timestamp_micros: int | None = None,
) -> dict:
    event: dict = {"name": name}
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    if clean:
        event["params"] = clean
    if timestamp_micros:
        event["timestamp_micros"] = timestamp_micros
    return {
        "client_id": client_id,
        "events": [event],
        "measurement_id": measurement_id,
        "api_secret": api_secret,
    }


async def send_event(
    measurement_id: str,
    api_secret: str,
    name: str,
    params: dict | None = None,
    client_id: str = "ss.anonymous",
    debug: bool = False,
) -> dict:
    """Send a single event through the Measurement Protocol.

    Returns the decoded response (debug endpoint returns validation messages).
    """
    if not measurement_id or not api_secret:
        return {"ok": False, "error": "measurement_id veya api_secret eksik"}
    event_params = dict(params or {})
    if debug:
        # Guarantees the event lands in DebugView even when the debug endpoint
        # is proxied or cached by an intermediary.
        event_params.setdefault("debug_mode", 1)
    payload = build_payload(measurement_id, api_secret, name, event_params, client_id)
    url = DEBUG_URL if debug else COLLECT_URL
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                params={"measurement_id": measurement_id, "api_secret": api_secret},
                json={
                    "client_id": payload["client_id"],
                    "events": payload["events"],
                },
            )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}
    if resp.status_code >= 400:
        return {"ok": False, "status": resp.status_code, "error": resp.text[:300]}
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:300]}
    if debug:
        return {"ok": True, "status": resp.status_code, "response": data}
    return {"ok": True, "status": resp.status_code}


async def send_batch(
    measurement_id: str,
    api_secret: str,
    events: list[dict],
) -> dict:
    """Send up to 20 events in one request (Measurement Protocol limit)."""
    if not measurement_id or not api_secret:
        return {"ok": False, "error": "measurement_id veya api_secret eksik"}
    if not events:
        return {"ok": True, "sent": 0}
    chunk = events[:20]
    mp_events = []
    for item in chunk:
        entry: dict = {"name": item["name"]}
        if item.get("params"):
            entry["params"] = item["params"]
        mp_events.append(entry)
    body = {
        "client_id": chunk[0].get("client_id") or "ss.anonymous",
        "events": mp_events,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                COLLECT_URL,
                params={"measurement_id": measurement_id, "api_secret": api_secret},
                json=body,
            )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}
    return {"ok": resp.status_code < 400, "status": resp.status_code, "sent": len(chunk)}
