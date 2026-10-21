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
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS credit_balance BIGINT NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS billing_period_end TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS usage_period_start TIMESTAMPTZ",
    """CREATE TABLE IF NOT EXISTS billing_events (
        stripe_event_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS credit_ledger (
        id BIGSERIAL PRIMARY KEY,
        user_id UUID,
        delta BIGINT NOT NULL,
        reason TEXT NOT NULL,
        stripe_ref TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_credit_ledger_user ON credit_ledger(user_id, created_at)",
    """CREATE TABLE IF NOT EXISTS plan_configs (
        key TEXT PRIMARY KEY,
        price_cents INT NOT NULL DEFAULT 0,
        token_budget BIGINT NOT NULL DEFAULT 1000000,
        agents INT NOT NULL DEFAULT 80,
        rounds INT NOT NULL DEFAULT 24,
        free_days INT NOT NULL DEFAULT 0,
        stripe_price_id TEXT NOT NULL DEFAULT '',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INT NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS credit_packs (
        key TEXT PRIMARY KEY,
        tokens BIGINT NOT NULL,
        price_cents INT NOT NULL,
        stripe_price_id TEXT NOT NULL DEFAULT '',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INT NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """INSERT INTO plan_configs (key, price_cents, token_budget, agents, rounds, free_days, sort_order)
       VALUES ('free', 0, 1000000, 80, 24, 0, 0),
              ('starter', 2900, 8000000, 150, 40, 0, 1),
              ('pro', 9900, 25000000, 300, 80, 0, 2)
       ON CONFLICT (key) DO NOTHING""",
    """INSERT INTO credit_packs (key, tokens, price_cents, sort_order)
       VALUES ('credit_5m', 5000000, 1900, 0)
       ON CONFLICT (key) DO NOTHING""",
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
