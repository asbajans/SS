"""Bootstrap helpers (idempotent)."""
from pathlib import Path

import structlog
from sqlalchemy import select, text

from app.config import settings
from app.db import AsyncSessionLocal
from app.models import Template, User
from app.security import hash_password
from engine.templates import builtin_templates

log = structlog.get_logger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "init.sql"

_MIGRATIONS = [
    "ALTER TABLE token_usage ADD COLUMN IF NOT EXISTS agent_id UUID",
    """CREATE TABLE IF NOT EXISTS templates (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        pack JSONB NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS privacy_requests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID,
        email TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        note TEXT,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        processed_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS idx_privacy_status ON privacy_requests(status, requested_at)",
]


async def ensure_schema() -> None:
    if not _SCHEMA_PATH.exists():
        log.warning("schema_file_missing", path=str(_SCHEMA_PATH))
        return
    async with AsyncSessionLocal() as s:
        existing = await s.scalar(select(text("to_regclass('users')")))
        if not existing:
            await s.execute(text(_SCHEMA_PATH.read_text(encoding="utf-8")))
            await s.commit()
            log.info("schema_applied", path=str(_SCHEMA_PATH))
        for stmt in _MIGRATIONS:
            await s.execute(text(stmt))
        await s.commit()


async def seed_templates() -> None:
    async with AsyncSessionLocal() as s:
        added = 0
        for tpl in builtin_templates():
            if await s.get(Template, tpl.key) is None:
                s.add(
                    Template(
                        key=tpl.key,
                        name=tpl.name,
                        description=tpl.description,
                        pack=tpl.to_pack(),
                        is_active=True,
                        is_builtin=True,
                    )
                )
                added += 1
        if added:
            await s.commit()
            log.info("templates_seeded", count=added)


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
