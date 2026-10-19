"""Bootstrap helpers (idempotent)."""
import structlog
from sqlalchemy import select

from app.config import settings
from app.db import AsyncSessionLocal
from app.models import User
from app.security import hash_password

log = structlog.get_logger(__name__)


async def create_first_admin() -> None:
    if not settings.first_admin_email or not settings.first_admin_password:
        return
    async with AsyncSessionLocal() as s:
        existing = (await s.scalars(select(User).where(User.email == settings.first_admin_email))).first()
        if existing is not None:
            return
        user = User(
            email=settings.first_admin_email,
            password_hash=hash_password(settings.first_admin_password),
            is_admin=True,
            plan="pro",
        )
        s.add(user)
        await s.commit()
        log.info("first_admin_created", email=settings.first_admin_email)
