"""Google entegrasyonlari: GA4, Search Console, Google Ads, Tag Manager.

Yonetici panelinden OAuth bilgileri girilir; butun API islemleri (olay
olusturma, custom dimension, key event, sitemap gonderme, rapor cektirme,
conversion sync, container publish) bu uclar uzerinden yurutulur.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import admin_only
from app.analytics import CUSTOM_DIMENSIONS, KEY_EVENTS
from app.auth import get_db
from app.ga4 import client_id_for, send_event, validate_event
from app.google import (
    PROVIDERS,
    SCOPES,
    GoogleAuthError,
    GoogleCredentials,
    api_request,
    clear_token_cache,
    oauth_authorize_url,
)
from app.models import AnalyticsEvent, GoogleIntegration, SeoSettings

router = APIRouter(prefix="/api/admin/google", tags=["admin-google"])

GA4_ADMIN = "https://analyticsadmin.googleapis.com/v1beta"
GA4_DATA = "https://analyticsdata.googleapis.com/v1beta"
SEARCH_CONSOLE = "https://searchconsole.googleapis.com/v1"
ADS_API = "https://googleads.googleapis.com/v18"
TAG_MANAGER = "https://tagmanager.googleapis.com/v2"

# GA4'da otomatik olusturulacak custom dimension'lar (event scope)
GA4_DIMENSIONS = CUSTOM_DIMENSIONS


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


class IntegrationIn(BaseModel):
    enabled: bool = False
    client_id: str = Field(default="", max_length=512)
    client_secret: str = Field(default="", max_length=512)
    refresh_token: str = Field(default="", max_length=2048)
    config: dict = Field(default_factory=dict)


class Ga4SetupIn(BaseModel):
    property_id: str = Field(default="", max_length=32)
    create_dimensions: bool = True
    create_key_events: bool = True
    create_conversion_event: bool = True


class SitemapIn(BaseModel):
    sitemap_url: str = Field(default="", max_length=512)


class AdsConversionIn(BaseModel):
    customer_id: str = Field(default="", max_length=32)
    event_name: str = Field(default="", max_length=64)
    label: str = Field(default="", max_length=128)
    value: str = Field(default="", max_length=32)


class TagManagerIn(BaseModel):
    container_id: str = Field(default="", max_length=64)
    measurement_id: str = Field(default="", max_length=64)
    publish: bool = False


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


async def _integration(db: AsyncSession, provider: str) -> GoogleIntegration | None:
    return (
        await db.scalars(select(GoogleIntegration).where(GoogleIntegration.provider == provider))
    ).first()


def _credentials(row: GoogleIntegration | None, provider: str) -> GoogleCredentials:
    if row is None:
        return GoogleCredentials(provider=provider)
    return GoogleCredentials(
        provider=provider,
        client_id=row.client_id or "",
        client_secret=row.client_secret or "",
        refresh_token=row.refresh_token or "",
        config=dict(row.config or {}),
    )


async def _ga4_settings(db: AsyncSession) -> SeoSettings:
    row = await db.get(SeoSettings, 1)
    if row is None:
        row = SeoSettings(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def _masked(row: GoogleIntegration | None, provider: str) -> dict:
    if row is None:
        return {
            "provider": provider,
            "enabled": False,
            "status": "not_configured",
            "client_id": "",
            "has_secret": False,
            "has_refresh_token": False,
            "config": {},
            "scopes": SCOPES.get(provider, []),
            "last_sync_at": None,
            "last_error": "",
        }
    return {
        "provider": provider,
        "enabled": row.enabled,
        "status": row.status,
        "client_id": row.client_id,
        "has_secret": bool(row.client_secret),
        "has_refresh_token": bool(row.refresh_token),
        "config": dict(row.config or {}),
        "scopes": SCOPES.get(provider, []),
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        "last_error": row.last_error or "",
    }


async def _mark(db: AsyncSession, row: GoogleIntegration, status: str, error: str = "") -> None:
    row.status = status
    row.last_error = error[:500]
    row.last_sync_at = datetime.now(UTC)
    await db.commit()


# --------------------------------------------------------------------------
# Integration CRUD
# --------------------------------------------------------------------------


@router.get("/integrations", dependencies=[Depends(admin_only)])
async def list_integrations(db: AsyncSession = Depends(get_db)) -> dict:
    rows = {
        r.provider: r
        for r in (await db.scalars(select(GoogleIntegration))).all()
    }
    seo = await _ga4_settings(db)
    return {
        "integrations": [_masked(rows.get(p), p) for p in PROVIDERS],
        "ga4": {
            "measurement_id": seo.analytics_id,
            "api_secret": bool(seo.ga4_api_secret),
            "property_id": seo.ga4_property_id,
            "server_side": seo.ga4_server_side,
        },
        "event_definitions": [
            {"name": name, "key_event": name in KEY_EVENTS} for name in KEY_EVENTS
        ],
        "dimensions": [{"name": n, "description": d} for n, d in GA4_DIMENSIONS],
    }


@router.put("/integrations/{provider}", dependencies=[Depends(admin_only)])
async def save_integration(
    provider: str, payload: IntegrationIn, db: AsyncSession = Depends(get_db)
) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="bilinmeyen provider")
    row = await _integration(db, provider)
    if row is None:
        row = GoogleIntegration(provider=provider)
        db.add(row)
    row.enabled = payload.enabled
    if payload.client_id:
        row.client_id = payload.client_id
    if payload.client_secret:
        row.client_secret = payload.client_secret
    if payload.refresh_token:
        row.refresh_token = payload.refresh_token
    row.config = payload.config or {}
    row.status = "configured" if row.enabled else "disabled"
    row.last_error = ""
    await db.commit()
    clear_token_cache(provider)
    return _masked(row, provider)


@router.delete("/integrations/{provider}", dependencies=[Depends(admin_only)])
async def delete_integration(provider: str, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, provider)
    if row is not None:
        await db.delete(row)
        await db.commit()
    clear_token_cache(provider)
    return {"ok": True}


@router.get("/integrations/{provider}/authorize-url", dependencies=[Depends(admin_only)])
async def authorize_url(provider: str, db: AsyncSession = Depends(get_db)) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail="bilinmeyen provider")
    row = await _integration(db, provider)
    client_id = row.client_id if row else ""
    if not client_id:
        raise HTTPException(status_code=400, detail="once client id kaydedin")
    redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    return {
        "url": oauth_authorize_url(provider, client_id, redirect_uri),
        "scopes": SCOPES.get(provider, []),
        "redirect_uri": redirect_uri,
    }


@router.post("/integrations/{provider}/test", dependencies=[Depends(admin_only)])
async def test_integration(provider: str, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, provider)
    cred = _credentials(row, provider)
    if not cred.is_complete:
        raise HTTPException(status_code=400, detail="OAuth bilgileri eksik")
    probes = {
        "ga4": lambda c: api_request(c, "GET", f"{GA4_ADMIN}/accountSummaries"),
        "search_console": lambda c: api_request(
            c, "GET", f"{SEARCH_CONSOLE}/sites"
        ),
        "google_ads": lambda c: api_request(
            c, "GET", f"{ADS_API}/customers"
        ),
        "tag_manager": lambda c: api_request(
            c, "GET", f"{TAG_MANAGER}/accounts"
        ),
    }
    try:
        data = await probes[provider](cred)
    except GoogleAuthError as exc:
        if row:
            await _mark(db, row, "error", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if row:
        await _mark(db, row, "connected")
    return {"ok": True, "provider": provider, "response": data}


# --------------------------------------------------------------------------
# GA4 — Measurement Protocol test + Admin API setup + Data API reports
# --------------------------------------------------------------------------


@router.post("/ga4/test-event", dependencies=[Depends(admin_only)])
async def ga4_test_event(db: AsyncSession = Depends(get_db)) -> dict:
    """Send a test event through the Measurement Protocol (debug endpoint)."""
    seo = await _ga4_settings(db)
    if not seo.analytics_id or not seo.ga4_api_secret:
        raise HTTPException(status_code=400, detail="measurement ID veya API secret eksik")
    if not seo.analytics_id.startswith("G-"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Measurement ID 'G-' ile baslamali, girilen: '{seo.analytics_id}'. "
                "GTM-... bir Tag Manager ID'sidir, buraya yazilmaz."
            ),
        )
    cid = client_id_for("admin-test")
    params = {"source": "admin_panel", "value": 0, "currency": "USD"}
    validation = await validate_event(
        seo.analytics_id, seo.ga4_api_secret, "ga4_test", params, client_id=cid
    )
    if not validation.get("ok"):
        validation.update({"event": "ga4_test", "client_id": cid, "stage": "validation"})
        return validation
    result = await send_event(
        seo.analytics_id,
        seo.ga4_api_secret,
        "ga4_test",
        params,
        client_id=cid,
        debug=True,
    )
    result.update(
        {
            "event": "ga4_test",
            "client_id": cid,
            "debug_view": "Sunucudan",
            "validationMessages": validation.get("validationMessages", []),
        }
    )
    return result


@router.put("/ga4", dependencies=[Depends(admin_only)])
async def save_ga4(payload: dict, db: AsyncSession = Depends(get_db)) -> dict:
    seo = await _ga4_settings(db)
    for key in ("ga4_api_secret", "ga4_property_id"):
        if key in payload:
            setattr(seo, key, str(payload[key] or "").strip())
    if "analytics_id" in payload:
        seo.analytics_id = str(payload["analytics_id"] or "").strip()
    if "ga4_server_side" in payload:
        seo.ga4_server_side = bool(payload["ga4_server_side"])
    await db.commit()
    await db.refresh(seo)
    return {
        "measurement_id": seo.analytics_id,
        "api_secret": bool(seo.ga4_api_secret),
        "property_id": seo.ga4_property_id,
        "server_side": seo.ga4_server_side,
    }


@router.post("/ga4/setup", dependencies=[Depends(admin_only)])
async def ga4_setup(payload: Ga4SetupIn, db: AsyncSession = Depends(get_db)) -> dict:
    """Create the custom dimensions and key events in GA4 via the Admin API."""
    row = await _integration(db, "ga4")
    cred = _credentials(row, "ga4")
    if not cred.is_complete:
        raise HTTPException(status_code=400, detail="GA4 OAuth bilgileri eksik")
    property_id = payload.property_id or cred.get("property_id")
    if not property_id:
        raise HTTPException(status_code=400, detail="GA4 property id gerekli")

    created: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    if payload.create_dimensions:
        try:
            existing = await api_request(
                cred, "GET", f"{GA4_ADMIN}/properties/{property_id}/customDimensions"
            )
            names = {d.get("displayName") for d in existing.get("customDimensions", [])}
        except GoogleAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        for name, description in GA4_DIMENSIONS:
            if name in names:
                skipped.append(name)
                continue
            try:
                await api_request(
                    cred,
                    "POST",
                    f"{GA4_ADMIN}/properties/{property_id}/customDimensions",
                    json_body={
                        "displayName": name,
                        "description": description,
                        "scope": "EVENT",
                        "disallowAdsPersonalization": False,
                    },
                )
                created.append(f"dimension:{name}")
            except GoogleAuthError as exc:
                errors.append(f"{name}: {exc}")

    if payload.create_key_events:
        try:
            existing = await api_request(
                cred, "GET", f"{GA4_ADMIN}/properties/{property_id}/keyEvents"
            )
            names = {k.get("eventName") for k in existing.get("keyEvents", [])}
        except GoogleAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        for name in KEY_EVENTS:
            if name in names:
                skipped.append(name)
                continue
            try:
                await api_request(
                    cred,
                    "POST",
                    f"{GA4_ADMIN}/properties/{property_id}/keyEvents",
                    json_body={"eventName": name, "countingMethod": "ONE_PER_EVENT"},
                )
                created.append(f"key_event:{name}")
            except GoogleAuthError as exc:
                errors.append(f"{name}: {exc}")

    if row:
        config = dict(row.config or {})
        config["property_id"] = property_id
        row.config = config
        await _mark(db, row, "connected", "; ".join(errors)[:400])

    return {"created": created, "skipped": skipped, "errors": errors}


@router.get("/ga4/report", dependencies=[Depends(admin_only)])
async def ga4_report(
    days: int = 30,
    property_id: str = "",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pull traffic / conversion / revenue numbers from the GA4 Data API."""
    row = await _integration(db, "ga4")
    cred = _credentials(row, "ga4")
    if not cred.is_complete:
        raise HTTPException(status_code=400, detail="GA4 OAuth bilgileri eksik")
    prop = property_id or cred.get("property_id")
    if not prop:
        raise HTTPException(status_code=400, detail="GA4 property id gerekli")

    end = datetime.now(UTC).date()
    start = end - datetime.timedelta(days=max(1, min(365, days))).date()

    async def run(body: dict) -> dict:
        try:
            return await api_request(
                cred,
                "POST",
                f"{GA4_DATA}/properties/{prop}:runReport",
                json_body=body,
            )
        except GoogleAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    totals = await run(
        {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "metrics": [
                {"name": "activeUsers"},
                {"name": "newUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
                {"name": "keyEvents"},
                {"name": "totalRevenue"},
            ],
        }
    )

    per_event = await run(
        {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": "eventName"}],
            "metrics": [{"name": "eventCount"}, {"name": "keyEvents"}, {"name": "totalRevenue"}],
            "limit": 40,
            "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
        }
    )

    def rows_of(report: dict) -> list[dict]:
        out = []
        for row_data in report.get("rows", []):
            dims = [d.get("value") for d in row_data.get("dimensionValues", [])]
            mets = [m.get("value") for m in row_data.get("metricValues", [])]
            out.append({"dimensions": dims, "metrics": mets})
        return out

    head = totals.get("totals") or []
    totals_row = head[0].get("metricValues", []) if head else []

    return {
        "property_id": prop,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "totals": {
            "active_users": totals_row[0].get("value") if len(totals_row) > 0 else "0",
            "new_users": totals_row[1].get("value") if len(totals_row) > 1 else "0",
            "sessions": totals_row[2].get("value") if len(totals_row) > 2 else "0",
            "page_views": totals_row[3].get("value") if len(totals_row) > 3 else "0",
            "key_events": totals_row[4].get("value") if len(totals_row) > 4 else "0",
            "revenue": totals_row[5].get("value") if len(totals_row) > 5 else "0",
        },
        "events": rows_of(per_event),
    }


@router.get("/ga4/queue", dependencies=[Depends(admin_only)])
async def ga4_queue(db: AsyncSession = Depends(get_db)) -> dict:
    rows = (
        await db.scalars(
            select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(100)
        )
    ).all()
    seo = await _ga4_settings(db)
    return {
        "server_side": bool(seo.ga4_api_secret),
        "pending": sum(1 for r in rows if r.delivered_at is None),
        "delivered": sum(1 for r in rows if r.delivered_at is not None),
        "events": [
            {
                "id": str(r.id),
                "name": r.name,
                "source": r.source,
                "value": float(r.value) if r.value is not None else None,
                "currency": r.currency,
                "params": r.params,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "delivered": r.delivered_at is not None,
            }
            for r in rows
        ],
    }


# --------------------------------------------------------------------------
# Search Console
# --------------------------------------------------------------------------


@router.post("/search-console/submit", dependencies=[Depends(admin_only)])
async def sc_submit(payload: SitemapIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, "search_console")
    cred = _credentials(row, "search_console")
    site_url = cred.get("site_url") or payload.sitemap_url
    if not cred.is_complete:
        raise HTTPException(status_code=400, detail="Search Console OAuth bilgileri eksik")
    if not site_url:
        raise HTTPException(status_code=400, detail="site URL gerekli")
    sitemap = payload.sitemap_url or f"{site_url.rstrip('/')}/sitemap.xml"
    try:
        data = await api_request(
            cred,
            "PUT",
            f"{SEARCH_CONSOLE}/sites/{site_url}/sitemaps/{sitemap}",
            raw_body="",
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "site_url": site_url, "sitemap": sitemap, "response": data}


@router.get("/search-console/sitemaps", dependencies=[Depends(admin_only)])
async def sc_sitemaps(db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, "search_console")
    cred = _credentials(row, "search_console")
    site_url = cred.get("site_url")
    if not cred.is_complete or not site_url:
        raise HTTPException(status_code=400, detail="Search Console ayarlari eksik")
    try:
        data = await api_request(
            cred, "GET", f"{SEARCH_CONSOLE}/sites/{site_url}/sitemaps"
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"site_url": site_url, "sitemaps": data.get("sitemaps", [])}


@router.get("/search-console/report", dependencies=[Depends(admin_only)])
async def sc_report(days: int = 28, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, "search_console")
    cred = _credentials(row, "search_console")
    site_url = cred.get("site_url")
    if not cred.is_complete or not site_url:
        raise HTTPException(status_code=400, detail="Search Console ayarlari eksik")
    end = datetime.now(UTC).date()
    start = end - datetime.timedelta(days=max(1, min(365, days))).date()
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["query", "page"],
        "rowLimit": 50,
    }
    try:
        data = await api_request(
            cred,
            "POST",
            f"{SEARCH_CONSOLE}/webmasters/v3/sites/{site_url}/searchAnalytics/query",
            json_body=body,
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"site_url": site_url, "rows": data.get("rows", [])}


# --------------------------------------------------------------------------
# Google Ads
# --------------------------------------------------------------------------


@router.get("/ads/report", dependencies=[Depends(admin_only)])
async def ads_report(days: int = 30, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, "google_ads")
    cred = _credentials(row, "google_ads")
    customer_id = cred.get("customer_id")
    if not cred.is_complete or not customer_id:
        raise HTTPException(status_code=400, detail="Google Ads ayarlari eksik")
    cid = customer_id.replace("-", "")
    query = {
        "customer_id": cid,
        "query": (
            "SELECT segments.date, metrics.impressions, metrics.clicks, "
            "metrics.cost_micros, metrics.conversions FROM customer "
            "WHERE segments.date DURING LAST_30_DAYS"
        ),
    }
    try:
        data = await api_request(
            cred, "POST", f"{ADS_API}/customers/{cid}/googleAds:searchStream", json_body=query
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"customer_id": customer_id, "results": data.get("results", [])}


@router.post("/ads/conversions", dependencies=[Depends(admin_only)])
async def ads_conversions(payload: AdsConversionIn, db: AsyncSession = Depends(get_db)) -> dict:
    """Create an Ads conversion action that mirrors a GA4 key event."""
    row = await _integration(db, "google_ads")
    cred = _credentials(row, "google_ads")
    customer_id = payload.customer_id or cred.get("customer_id")
    if not cred.is_complete or not customer_id:
        raise HTTPException(status_code=400, detail="Google Ads ayarlari eksik")
    cid = customer_id.replace("-", "")
    name = payload.event_name or "sign_up"
    body = {
        "customer_id": cid,
        "conversion_action": {
            "name": payload.label or name,
            "category": "PAGE_VIEW",
            "type": "WEBPAGE",
            "primary_for_goal": True,
            "origin": "WEB",
            "value_settings": {
                "default_value": 0,
                "default_currency_code": "USD",
                "always_use_default_value": True,
            },
        },
    }
    try:
        data = await api_request(
            cred,
            "POST",
            f"{ADS_API}/customers/{cid}/googleAds:modifyGoogleAds",
            json_body=body,
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "customer_id": customer_id, "event": name, "response": data}


# --------------------------------------------------------------------------
# Tag Manager
# --------------------------------------------------------------------------


@router.get("/tag-manager/containers", dependencies=[Depends(admin_only)])
async def tm_containers(db: AsyncSession = Depends(get_db)) -> dict:
    row = await _integration(db, "tag_manager")
    cred = _credentials(row, "tag_manager")
    if not cred.is_complete:
        raise HTTPException(status_code=400, detail="Tag Manager OAuth bilgileri eksik")
    try:
        data = await api_request(cred, "GET", f"{TAG_MANAGER}/accounts")
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"accounts": data.get("accounts", [])}


@router.post("/tag-manager/setup", dependencies=[Depends(admin_only)])
async def tm_setup(payload: TagManagerIn, db: AsyncSession = Depends(get_db)) -> dict:
    """Create a GA4 config tag in a Tag Manager container (optionally publish)."""
    row = await _integration(db, "tag_manager")
    cred = _credentials(row, "tag_manager")
    if not cred.is_complete:
        raise HTTPException(status_code=400, detail="Tag Manager OAuth bilgileri eksik")
    public_id = (payload.container_id or cred.get("container_id") or "").strip()
    if not public_id:
        raise HTTPException(status_code=400, detail="container ID gerekli (GTM-XXXXXXX)")
    measurement_id = payload.measurement_id or cred.get("measurement_id") or ""
    if not measurement_id:
        raise HTTPException(status_code=400, detail="measurement ID gerekli")

    try:
        account_id, container = await _find_tm_container(cred, public_id)
        if not container:
            raise HTTPException(
                status_code=404,
                detail=f"Kapsayici bulunamadi: {public_id}. OAuth hesabinda gorunur mu?",
            )
        container_id = container["containerId"]
        base = f"{TAG_MANAGER}/accounts/{account_id}/containers/{container_id}"
        workspaces = await api_request(cred, "GET", f"{base}/workspaces")
        workspace_id = (workspaces.get("workspace") or [{}])[0].get("workspaceId")
        if not workspace_id:
            raise HTTPException(status_code=400, detail="Varsayilan workspace bulunamadi")

        tag_body = {
            "name": "GA4 Configuration",
            "type": "gaawc",
            "parameter": [
                {"type": "template", "key": "measurementId", "value": measurement_id}
            ],
            "firingTriggerId": ["2147479553"],
        }
        tag = await api_request(
            cred, "POST", f"{base}/workspaces/{workspace_id}/tags", json_body=tag_body
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    published = False
    if payload.publish:
        try:
            version = await api_request(
                cred,
                "POST",
                f"{base}/workspaces/{workspace_id}:create_version",
                json_body={"name": "GA4 setup", "notes": "GA4 config tag (panel)"},
            )
            version_id = (version.get("containerVersion") or {}).get("containerVersionId")
            if version_id:
                await api_request(
                    cred, "POST", f"{base}/versions/{version_id}:publish", json_body={}
                )
                published = True
        except GoogleAuthError as exc:
            return {
                "ok": True,
                "published": False,
                "error": str(exc),
                "container": container.get("publicId"),
                "tag": tag,
            }

    return {
        "ok": True,
        "published": published,
        "container": container.get("publicId"),
        "workspace": workspace_id,
        "tag": tag,
    }


async def _find_tm_container(
    cred: GoogleCredentials, public_id: str
) -> tuple[str | None, dict | None]:
    """Resolve a GTM-XXXXXXX public ID to its numeric account/container."""
    accounts = await api_request(cred, "GET", f"{TAG_MANAGER}/accounts")
    for account in accounts.get("account", []):
        account_id = account.get("accountId")
        if not account_id:
            continue
        containers = await api_request(
            cred, "GET", f"{TAG_MANAGER}/accounts/{account_id}/containers"
        )
        for container in containers.get("container", []):
            if public_id in (container.get("publicId"), container.get("containerId")):
                return account_id, container
    return None, None

