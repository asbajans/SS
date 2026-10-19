"""Security: Argon2 + JWT."""
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

ph = PasswordHasher()


def hash_password(raw: str) -> str:
    return ph.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False
    return True


def make_token(user_id: str, is_admin: bool = False) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "adm": is_admin,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_min),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_alg)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_alg])
