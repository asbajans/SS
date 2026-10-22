"""Google API erişimi: OAuth2 refresh-token akışı + ortak HTTP yardımcıları.

Dört entegrasyon aynı credential modelini kullanır:
  - ga4             -> GA4 Admin API (custom dimension / key event) + Data API (rapor)
  - search_console  -> Search Console API (sitemap + performans)
  - google_ads      -> Google Ads API (conversion + kampanya)
  - tag_manager     -> Tag Manager API (tag/trigger/variable + publish)

Yalnizca OAuth2 "installed app" akisi desteklenir: admin panelden client id,
client secret ve refresh token girilir; access token otomatik yenilenir.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES: dict[str, list[str]] = {
    "ga4": [
        "https://www.googleapis.com/auth/analytics.edit",
        "https://www.googleapis.com/auth/analytics.readonly",
    ],
    "search_console": [
        "https://www.googleapis.com/auth/webmasters",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ],
    "google_ads": [
        "https://www.googleapis.com/auth/adwords",
    ],
    "tag_manager": [
        "https://www.googleapis.com/auth/tagmanager.edit.containers",
        "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
        "https://www.googleapis.com/auth/tagmanager.publish",
        "https://www.googleapis.com/auth/tagmanager.readonly",
        "https://www.googleapis.com/auth/tagmanager.manage.accounts",
    ],
}

PROVIDERS = tuple(SCOPES)


@dataclass
class GoogleCredentials:
    provider: str
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    config: dict = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        value = self.config.get(key, default)
        return str(value) if value is not None else default

    @property
    def is_complete(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)


class GoogleAuthError(RuntimeError):
    """Raised when the Google API rejects our credentials."""


# access token cache: provider -> (token, expires_at)
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


def clear_token_cache(provider: str | None = None) -> None:
    if provider:
        _TOKEN_CACHE.pop(provider, None)
    else:
        _TOKEN_CACHE.clear()


async def access_token(cred: GoogleCredentials) -> str:
    """Return a valid access token, refreshing the refresh token if needed."""
    if not cred.is_complete:
        raise GoogleAuthError(
            f"{cred.provider}: eksik OAuth bilgileri (client_id / client_secret / refresh_token)"
        )
    cached = _TOKEN_CACHE.get(cred.provider)
    if cached and cached[1] > time.time() + 60:
        return cached[0]

    payload = {
        "client_id": cred.client_id,
        "client_secret": cred.client_secret,
        "refresh_token": cred.refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(TOKEN_URL, data=payload)
    if resp.status_code != 200:
        detail = resp.text[:400]
        raise GoogleAuthError(f"token yenilenemedi ({resp.status_code}): {detail}")
    data = resp.json()
    token = data.get("access_token", "")
    if not token:
        raise GoogleAuthError("token yanitinda access_token yok")
    expires_in = int(data.get("expires_in") or 3600)
    _TOKEN_CACHE[cred.provider] = (token, time.time() + expires_in)
    return token


async def api_request(
    cred: GoogleCredentials,
    method: str,
    url: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
    raw_body: str | None = None,
) -> dict:
    """Call a Google API with the provider's access token."""
    token = await access_token(cred)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            data=raw_body,
            params=params,
        )
    if resp.status_code >= 400:
        raise GoogleAuthError(f"{resp.status_code}: {resp.text[:500]}")
    if not resp.text:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


def oauth_authorize_url(provider: str, client_id: str, redirect_uri: str) -> str:
    """URL the admin opens to grant access and obtain a refresh token."""
    from urllib.parse import urlencode

    scopes = " ".join(SCOPES.get(provider, []))
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def oauth_token_exchange(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for tokens (sync helper for the CLI)."""
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(TOKEN_URL, data=payload)
    if resp.status_code != 200:
        raise GoogleAuthError(f"token degisimi basarisiz ({resp.status_code}): {resp.text[:400]}")
    return resp.json()
