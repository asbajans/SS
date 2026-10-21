"""Google Identity Services login: ID token verification.

Uses the Google Identity Services (GIS) button on the SPA. The browser sends the
Google ID token (JWT) to our API; we verify the signature against Google's JWKS
and the audience against the configured client id. No Google client secret is
needed in this flow, so only a public client id is stored in the environment.
"""
import httpx
import jwt

from app.config import settings

try:
    from jwt import PyJWKClient
except Exception:  # noqa: BLE001 - optional crypto backend
    PyJWKClient = None  # type: ignore[assignment]

JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


class GoogleAuthError(Exception):
    """Raised when a Google credential cannot be trusted."""


def google_client_ids() -> list[str]:
    raw = settings.google_client_id or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


def google_login_enabled() -> bool:
    return bool(google_client_ids())


def _decode_with_jwks(id_token: str, audience: list[str]) -> dict:
    if PyJWKClient is None:
        raise RuntimeError("cryptography backend unavailable")
    signing_key = PyJWKClient(JWKS_URL).get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        options={"require": ["exp", "iat", "iss", "aud", "email"]},
    )


def _decode_with_tokeninfo(id_token: str, audience: list[str]) -> dict:
    with httpx.Client(timeout=8.0) as client:
        response = client.get(TOKENINFO_URL, params={"id_token": id_token})
    if response.status_code != 200:
        raise GoogleAuthError("google token could not be validated")
    claims = response.json()
    if claims.get("aud") not in audience:
        raise GoogleAuthError("token audience mismatch")
    return claims


def claims_to_identity(claims: dict) -> dict:
    issuer = claims.get("iss")
    if issuer not in GOOGLE_ISSUERS:
        raise GoogleAuthError("invalid issuer")
    email = str(claims.get("email") or "").strip().lower()
    if not email:
        raise GoogleAuthError("email missing in google token")
    verified = claims.get("email_verified")
    if verified is not True and str(verified).lower() not in {"true", "1"}:
        raise GoogleAuthError("google email is not verified")
    return {"email": email, "sub": str(claims.get("sub") or "")}


def verify_google_id_token(id_token: str) -> dict:
    audience = google_client_ids()
    if not audience:
        raise GoogleAuthError("google login is not configured")
    if not id_token or len(id_token) > 4096:
        raise GoogleAuthError("missing credential")
    claims: dict
    try:
        claims = _decode_with_jwks(id_token, audience)
    except jwt.InvalidAudienceError as exc:
        raise GoogleAuthError("token audience mismatch") from exc
    except jwt.InvalidTokenError as exc:
        raise GoogleAuthError("invalid google token") from exc
    except Exception:
        try:
            claims = _decode_with_tokeninfo(id_token, audience)
        except GoogleAuthError:
            raise
        except Exception as exc:
            raise GoogleAuthError("invalid google token") from exc
    return claims_to_identity(claims)
