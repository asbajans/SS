"""Google sign-in: token verification helpers and route wiring."""
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.google_auth import (
    GoogleAuthError,
    claims_to_identity,
    google_client_ids,
    google_login_enabled,
    verify_google_id_token,
)
from app.main import app


def test_client_ids_parsing(monkeypatch):
    monkeypatch.setattr("app.google_auth.settings.google_client_id", " id-a , id-b ,")
    assert google_client_ids() == ["id-a", "id-b"]
    assert google_login_enabled() is True


def test_disabled_without_client_id(monkeypatch):
    monkeypatch.setattr("app.google_auth.settings.google_client_id", "")
    assert google_client_ids() == []
    assert google_login_enabled() is False
    with pytest.raises(GoogleAuthError):
        verify_google_id_token("whatever")


def test_claims_to_identity_normalizes_email():
    claims = {
        "iss": "https://accounts.google.com",
        "email": " User@Example.com ",
        "email_verified": True,
        "sub": "123",
    }
    identity = claims_to_identity(claims)
    assert identity == {"email": "user@example.com", "sub": "123"}


def test_claims_to_identity_rejects_bad_input():
    good_iss = "https://accounts.google.com"
    with pytest.raises(GoogleAuthError):
        claims_to_identity({"iss": "evil.example.com", "email": "a@b.com", "email_verified": True})
    with pytest.raises(GoogleAuthError):
        claims_to_identity({"iss": good_iss, "email": "", "email_verified": True})
    with pytest.raises(GoogleAuthError):
        claims_to_identity({"iss": good_iss, "email": "a@b.com", "email_verified": False})


def test_routes_registered():
    paths = set(app.openapi().get("paths", {}))
    assert "/api/auth/google" in paths
    assert "/api/auth/google/config" in paths


def _rsa_pair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _id_token(private_pem, **claims):
    payload = {
        "iss": "https://accounts.google.com",
        "aud": "cid-1",
        "email": "user@example.com",
        "email_verified": True,
        "sub": "google-sub-1",
        "iat": 1_700_000_000,
        "exp": 4_100_000_000,
    }
    payload.update(claims)
    return jwt.encode(payload, private_pem, algorithm="RS256")


def test_verify_google_id_token_valid(monkeypatch):
    private_pem, public_pem = _rsa_pair()
    monkeypatch.setattr("app.google_auth.settings.google_client_id", "cid-1")

    class FakeJwkClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            class Key:
                key = public_pem

            return Key()

    monkeypatch.setattr("app.google_auth.PyJWKClient", FakeJwkClient)
    identity = verify_google_id_token(_id_token(private_pem))
    assert identity == {"email": "user@example.com", "sub": "google-sub-1"}


def test_verify_google_id_token_rejects_foreign_audience(monkeypatch):
    private_pem, public_pem = _rsa_pair()
    monkeypatch.setattr("app.google_auth.settings.google_client_id", "cid-1")

    class FakeJwkClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            class Key:
                key = public_pem

            return Key()

    monkeypatch.setattr("app.google_auth.PyJWKClient", FakeJwkClient)
    with pytest.raises(GoogleAuthError):
        verify_google_id_token(_id_token(private_pem, aud="other-client"))


def test_verify_google_id_token_rejects_unverified_email(monkeypatch):
    private_pem, public_pem = _rsa_pair()
    monkeypatch.setattr("app.google_auth.settings.google_client_id", "cid-1")

    class FakeJwkClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            class Key:
                key = public_pem

            return Key()

    monkeypatch.setattr("app.google_auth.PyJWKClient", FakeJwkClient)
    with pytest.raises(GoogleAuthError):
        verify_google_id_token(_id_token(private_pem, email_verified=False))
