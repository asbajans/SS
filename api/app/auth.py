"""Auth routes + request-user dependency."""
import asyncio
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import (
    LOGIN,
    METHOD_EMAIL,
    METHOD_GOOGLE,
    SIGN_UP,
    dispatch_pending,
    record,
    signup_params,
)
from app.db import AsyncSessionLocal
from app.google_auth import (
    GoogleAuthError,
    google_client_ids,
    google_login_enabled,
    verify_google_id_token,
)
from app.models import User
from app.security import decode_token, hash_password, make_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginIn(BaseModel):
    credential: str


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as s:
        yield s


async def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = decode_token(cred.credentials)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="invalid token") from e
    user = (await db.scalars(select(User).where(User.id == payload["sub"]))).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)) -> dict:
    existing = (await db.scalars(select(User).where(User.email == data.email))).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    await db.flush()
    await record(
        db,
        SIGN_UP,
        user_id=user.id,
        params=signup_params(METHOD_EMAIL, user.plan or "free"),
    )
    await db.commit()
    await dispatch_pending(db)
    return {
        "id": user.id,
        "email": user.email,
        "is_new": True,
        "signup_method": METHOD_EMAIL,
        "token": make_token(str(user.id), user.is_admin),
    }


@router.post("/login")
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)) -> dict:
    user = (await db.scalars(select(User).where(User.email == data.email))).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    await record(
        db,
        LOGIN,
        user_id=user.id,
        params=signup_params(METHOD_EMAIL, user.plan or "free"),
    )
    await db.commit()
    await dispatch_pending(db)
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin,
            "signup_method": METHOD_EMAIL,
            "token": make_token(str(user.id), user.is_admin)}


@router.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email, "plan": user.plan, "is_admin": user.is_admin}


@router.get("/google/config")
async def google_config() -> dict:
    client_ids = google_client_ids()
    return {"enabled": bool(client_ids), "client_id": client_ids[0] if client_ids else ""}


@router.post("/google")
async def google_login(data: GoogleLoginIn, db: AsyncSession = Depends(get_db)) -> dict:
    if not google_login_enabled():
        raise HTTPException(status_code=503, detail="google login is not enabled")
    try:
        identity = await asyncio.to_thread(verify_google_id_token, data.credential)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    email = identity["email"]
    google_sub = identity["sub"] or None
    user = (await db.scalars(select(User).where(User.email == email))).first()
    is_new = user is None
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            google_id=google_sub,
        )
        db.add(user)
        await db.flush()
        await record(
            db,
            SIGN_UP,
            user_id=user.id,
            params=signup_params(METHOD_GOOGLE, user.plan or "free"),
        )
    else:
        if user.google_id is None and google_sub:
            user.google_id = google_sub
        await record(
            db,
            LOGIN,
            user_id=user.id,
            params=signup_params(METHOD_GOOGLE, user.plan or "free"),
        )
    await db.commit()
    await db.refresh(user)
    await dispatch_pending(db)
    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_new": is_new,
        "signup_method": METHOD_GOOGLE,
        "token": make_token(str(user.id), user.is_admin),
    }
