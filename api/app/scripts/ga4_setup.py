"""GA4 olay (event) ve custom dimension tanimlari.

Bu dosya iki sey saglar:

1) Uygulamanin gonderdigi olay sozlesmesi (event names + params).
2) GA4 Admin API ile bu custom dimension / key event tanimlarini
   programatik olarak olusturmak icin kullanilabilen yardimci.

Kullanim (GA4 Admin API ile otomatik kurulum):

    # once OAuth jetonu (bir kez):
    python -m app.scripts.ga4_setup --auth-code 4/0AY...
    # sonra:
    python -m app.scripts.ga4_setup --property 123456789

    # ya da sadece tanimlari gormek icin:
    python -m app.scripts.ga4_setup --dry-run

Alternatif: GA4 arayuzunden elle olusturmak icin EVENT_DEFINITIONS
ve CUSTOM_DIMENSIONS tablolarindaki isimleri kullanin.
"""
from __future__ import annotations

import argparse
import os
import sys

# --------------------------------------------------------------------------
# Olay sozlesmesi
# --------------------------------------------------------------------------

# (event_name, description, is_key_event)
EVENT_DEFINITIONS: list[tuple[str, str, bool]] = [
    ("sign_up", "Yeni hesap olusturuldu (google/epoosta ayrimli)", True),
    ("login", "Giris yapildi", False),
    ("checkout_start", "Odeme sayfasi acildi", False),
    ("purchase", "Odeme tamamlandi (paket satin alindi)", True),
    ("subscription_renew", "Periyodik abonelik yenilemesi", True),
    ("plan_change", "Plan degisikligi (yukseltme/indirim)", False),
]

# (param_name, scope, description)
CUSTOM_DIMENSIONS: list[tuple[str, str, str]] = [
    ("signup_method", "EVENT", "Uyelik yontemi: google | email"),
    ("method", "EVENT", "GA4 standart uyelik yontemi (google|email)"),
    ("plan", "EVENT", "Satin alinan/aktif plan"),
    ("item_type", "EVENT", "subscription | credit_pack"),
    ("payment_type", "EVENT", "subscription | one_time"),
    ("item_name", "EVENT", "Urun adi (plan_starter, credit_5000000 ...)"),
    ("transaction_id", "EVENT", "Odeme islem kimligi (Stripe session id)"),
]

# GA4'da olusturulacak "key event" (donusum) listesi
KEY_EVENTS = [name for name, _, is_key in EVENT_DEFINITIONS if is_key]


# --------------------------------------------------------------------------
# GA4 Admin API (Data Admin API - analyticsadmin.googleapis.com)
# --------------------------------------------------------------------------


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    import httpx

    resp = httpx.request(
        method,
        url,
        json=body,
        headers=_headers(token),
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise SystemExit(f"GA4 API hatasi {resp.status_code}: {resp.text[:500]}")
    if not resp.text:
        return {}
    return resp.json()


def list_custom_dimensions(property_id: str, token: str) -> list[dict]:
    url = (
        f"https://analyticsadmin.googleapis.com/v1beta/properties/{property_id}"
        "/customDimensions"
    )
    return _request("GET", url, token).get("customDimensions", [])


def create_custom_dimension(property_id: str, token: str, name: str, description: str) -> dict:
    url = (
        f"https://analyticsadmin.googleapis.com/v1beta/properties/{property_id}"
        "/customDimensions"
    )
    body = {
        "displayName": name,
        "description": description,
        "scope": "EVENT",
        "disallowAdsPersonalization": False,
    }
    return _request("POST", url, token, body)


def _token_from_env() -> str:
    token = os.environ.get("GA4_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("GA4_ACCESS_TOKEN tanimli degil (OAuth ile alinmis erisim jetonu)")
    return token


def list_key_events(property_id: str, token: str) -> list[dict]:
    url = (
        f"https://analyticsadmin.googleapis.com/v1beta/properties/{property_id}"
        "/keyEvents"
    )
    return _request("GET", url, token).get("keyEvents", [])


def create_key_event(property_id: str, token: str, name: str) -> dict:
    url = (
        f"https://analyticsadmin.googleapis.com/v1beta/properties/{property_id}"
        "/keyEvents"
    )
    body = {"eventName": name, "countingMethod": "ONE_PER_EVENT"}
    return _request("POST", url, token, body)


def main() -> int:
    parser = argparse.ArgumentParser(description="GA4 olay ve custom dimension kurulumu")
    parser.add_argument("--property", default="", help="GA4 property id (orn. 123456789)")
    parser.add_argument("--dry-run", action="store_true", help="sadece tanimlari goster")
    args = parser.parse_args()

    if args.dry_run:
        print("Olaylar (key event = *):")
        for name, desc, is_key in EVENT_DEFINITIONS:
            print(f"  {'*' if is_key else ' '} {name:24} {desc}")
        print("\nCustom dimensions (EVENT scope):")
        for name, _scope, desc in CUSTOM_DIMENSIONS:
            print(f"    {name:18} {desc}")
        return 0

    if not args.property:
        sys.exit("--property zorunlu")
    token = _token_from_env()
    existing_dims = {d.get("displayName") for d in list_custom_dimensions(args.property, token)}
    for name, _scope, desc in CUSTOM_DIMENSIONS:
        if name in existing_dims:
            print(f"= {name} zaten var")
            continue
        try:
            create_custom_dimension(args.property, token, name, desc)
            print(f"+ custom dimension olusturuldu: {name}")
        except SystemExit as exc:
            print(f"! {name}: {exc}")

    existing_keys = {k.get("eventName") for k in list_key_events(args.property, token)}
    for name in KEY_EVENTS:
        if name in existing_keys:
            print(f"= key event zaten var: {name}")
            continue
        try:
            create_key_event(args.property, token, name)
            print(f"+ key event olusturuldu: {name}")
        except SystemExit as exc:
            print(f"! {name}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
