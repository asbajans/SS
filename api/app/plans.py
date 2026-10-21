"""DB-backed plan catalog, credit packs and free-trial helpers."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import CreditPack, PlanConfig

DEFAULT_PLANS = (
    {"key": "free", "price_cents": 0, "token_budget": 1_000_000, "agents": 80, "rounds": 24},
    {"key": "starter", "price_cents": 2900, "token_budget": 8_000_000, "agents": 150, "rounds": 40},
    {"key": "pro", "price_cents": 9900, "token_budget": 25_000_000, "agents": 300, "rounds": 80},
)
DEFAULT_PACKS = (
    {"key": "credit_5m", "tokens": 5_000_000, "price_cents": 1900},
)


def _env_price_id(key: str) -> str:
    if key == "starter":
        return settings.stripe_price_starter or settings.stripe_monthly_price_id
    if key == "pro":
        return settings.stripe_price_pro
    if key == "credit_5m":
        return settings.stripe_price_credit_5m
    return ""


def _row_dict(row, free_days: int = 0) -> dict:
    price_id = row.stripe_price_id or _env_price_id(row.key)
    return {
        "key": row.key,
        "price_cents": row.price_cents,
        "price": row.price_cents / 100,
        "token_budget": row.token_budget,
        "agents": row.agents,
        "rounds": row.rounds,
        "free_days": free_days,
        "stripe_price_id": row.stripe_price_id,
        "price_id": price_id,
        "is_active": row.is_active,
        "checkout_enabled": bool(settings.stripe_secret_key and price_id),
    }


def _default_dict(plan: dict) -> dict:
    price_id = _env_price_id(plan["key"])
    return {
        **plan,
        "price": plan["price_cents"] / 100,
        "free_days": 0,
        "stripe_price_id": "",
        "price_id": price_id,
        "is_active": True,
        "checkout_enabled": bool(settings.stripe_secret_key and price_id),
    }


async def plan_catalog(db: AsyncSession) -> list[dict]:
    rows = (
        await db.scalars(
            select(PlanConfig).where(PlanConfig.is_active.is_(True)).order_by(PlanConfig.sort_order)
        )
    ).all()
    if not rows:
        return [_default_dict(p) for p in DEFAULT_PLANS]
    return [_row_dict(r, r.free_days if r.key == "free" else 0) for r in rows]


async def credit_catalog(db: AsyncSession) -> list[dict]:
    rows = (
        await db.scalars(
            select(CreditPack).where(CreditPack.is_active.is_(True)).order_by(CreditPack.sort_order)
        )
    ).all()
    if not rows:
        return [
            {
                **p,
                "price": p["price_cents"] / 100,
                "price_id": _env_price_id(p["key"]),
                "is_active": True,
                "checkout_enabled": bool(settings.stripe_secret_key and _env_price_id(p["key"])),
            }
            for p in DEFAULT_PACKS
        ]
    return [
        {
            "key": r.key,
            "tokens": r.tokens,
            "price_cents": r.price_cents,
            "price": r.price_cents / 100,
            "stripe_price_id": r.stripe_price_id,
            "price_id": r.stripe_price_id or _env_price_id(r.key),
            "is_active": r.is_active,
            "checkout_enabled": bool(
                settings.stripe_secret_key and (r.stripe_price_id or _env_price_id(r.key))
            ),
        }
        for r in rows
    ]


async def get_plan(db: AsyncSession, key: str) -> dict | None:
    return next((p for p in await plan_catalog(db) if p["key"] == key), None)


async def get_plan_by_price(db: AsyncSession, price_id: str | None) -> dict | None:
    if not price_id:
        return None
    return next((p for p in await plan_catalog(db) if p["price_id"] == price_id), None)


async def get_plan_limits(db: AsyncSession, key: str | None) -> dict:
    plan = await get_plan(db, key or "free")
    if plan is None and key:
        row = await db.get(PlanConfig, key)
        if row is not None:
            plan = _row_dict(row, row.free_days if row.key == "free" else 0)
    if plan is None:
        return {
            "plan": "free",
            "token_budget": DEFAULT_PLANS[0]["token_budget"],
            "agents": DEFAULT_PLANS[0]["agents"],
            "rounds": DEFAULT_PLANS[0]["rounds"],
            "free_days": 0,
        }
    return {
        "plan": plan["key"],
        "token_budget": plan["token_budget"],
        "agents": plan["agents"],
        "rounds": plan["rounds"],
        "free_days": plan["free_days"],
    }


def free_until(created_at: datetime | None, free_days: int) -> datetime | None:
    if not created_at or free_days <= 0:
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return created_at + timedelta(days=free_days)


def free_access_expired(
    created_at: datetime | None, free_days: int, now: datetime | None = None
) -> bool:
    if free_days <= 0:
        return False
    end = free_until(created_at, free_days)
    if end is None:
        return False
    return (now or datetime.now(UTC)) >= end
