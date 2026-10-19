"""Auth routes + request-user dependency."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
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
    await db.commit()
    return {"id": user.id, "email": user.email, "token": make_token(str(user.id), user.is_admin)}


@router.post("/login")
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)) -> dict:
    user = (await db.scalars(select(User).where(User.email == data.email))).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin,
            "token": make_token(str(user.id), user.is_admin)}


@router.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email, "plan": user.plan, "is_admin": user.is_admin}
