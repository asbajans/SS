"""Admin router: manage per-task model configs (model, quotas, fallbacks)."""
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.config import settings
from app.llm_gateway.config_resolver import invalidate_config
from app.models import (
    CreditPack,
    ModelConfig,
    PlanConfig,
    PrivacyRequest,
    TokenUsage,
    User,
)
from app.plans import DEFAULT_PACKS, DEFAULT_PLANS, free_access_expired, free_until

router = APIRouter(prefix="/api/admin", tags=["admin"])

_OR_CACHE: dict = {"ts": 0.0, "models": []}
_CACHE_TTL = 600.0


def admin_only(user=Depends(current_user)) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")


class PlanIn(BaseModel):
    price: float = Field(ge=0)
    token_budget: int = Field(ge=0)
    agents: int = Field(ge=1, le=300)
    rounds: int = Field(ge=1, le=80)
    free_days: int = Field(default=0, ge=0, le=3650)
    stripe_price_id: str = ""
    is_active: bool = True


class CreditPackIn(BaseModel):
    tokens: int = Field(gt=0)
    price: float = Field(ge=0)
    stripe_price_id: str = ""
    is_active: bool = True


class ModelConfigIn(BaseModel):
    model: str
    fallbacks: list[str] = []
    max_tokens: int
    temperature: float = 0.7
    rpm: int = 60
    tpm: int = 200000
    daily_budget_tokens: int = 3000000
    monthly_budget_tokens: int = 30000000
    cost_in_usd_per_mtok: float = 0.0
    cost_out_usd_per_mtok: float = 0.0
    enabled: bool = True


@router.get("/models", dependencies=[Depends(admin_only)])
async def list_models(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(ModelConfig))).all()
    return [
        {
            "task_key": m.task_key,
            "model": m.model,
            "fallbacks": m.fallbacks or [],
            "max_tokens": m.max_tokens,
            "temperature": float(m.temperature),
            "rpm": m.rpm,
            "tpm": m.tpm,
            "daily_budget_tokens": m.daily_budget_tokens,
            "monthly_budget_tokens": m.monthly_budget_tokens,
            "cost_in_usd_per_mtok": float(m.cost_in_usd_per_mtok),
            "cost_out_usd_per_mtok": float(m.cost_out_usd_per_mtok),
            "enabled": m.enabled,
        }
        for m in rows
    ]


@router.put("/models/{task_key}", dependencies=[Depends(admin_only)])
async def upsert_model(task_key: str, data: ModelConfigIn, db: AsyncSession = Depends(get_db)):
    batch = [m for m in [data.model, *data.fallbacks] if m.endswith(":batch")]
    if batch:
        raise HTTPException(
            status_code=400,
            detail="Batch variants (:batch) do not support chat completions; pick the standard model id",
        )
    cfg = (await db.scalars(select(ModelConfig).where(ModelConfig.task_key == task_key))).first()
    if cfg is None:
        cfg = ModelConfig(task_key=task_key)
    cfg.model = data.model
    cfg.fallbacks = data.fallbacks
    cfg.max_tokens = data.max_tokens
    cfg.temperature = data.temperature
    cfg.rpm = data.rpm
    cfg.tpm = data.tpm
    cfg.daily_budget_tokens = data.daily_budget_tokens
    cfg.monthly_budget_tokens = data.monthly_budget_tokens
    cfg.cost_in_usd_per_mtok = data.cost_in_usd_per_mtok
    cfg.cost_out_usd_per_mtok = data.cost_out_usd_per_mtok
    cfg.enabled = data.enabled
    db.add(cfg)
    await db.commit()
    invalidate_config(task_key)
    return {"task_key": task_key, "saved": True}


@router.get("/openrouter/models", dependencies=[Depends(admin_only)])
async def openrouter_models(refresh: bool = False):
    now = time.time()
    if not refresh and _OR_CACHE["models"] and now - _OR_CACHE["ts"] < _CACHE_TTL:
        return _OR_CACHE["models"]
    try:
        headers = {}
        if settings.openrouter_api_key:
            headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{settings.openrouter_base_url}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"OpenRouter model listesi alınamadı: {exc}"
        ) from None

    models = []
    for item in data:
        pricing = item.get("pricing") or {}
        try:
            prompt = float(pricing.get("prompt", 0) or 0) * 1_000_000
            completion = float(pricing.get("completion", 0) or 0) * 1_000_000
        except (TypeError, ValueError):
            prompt = completion = 0.0
        models.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or item.get("id"),
                "context_length": item.get("context_length"),
                "prompt_per_mtok": round(prompt, 4),
                "completion_per_mtok": round(completion, 4),
            }
        )
    models.sort(key=lambda m: m["id"] or "")
    _OR_CACHE.update(ts=now, models=models)
    return models


@router.get("/plans", dependencies=[Depends(admin_only)])
async def admin_plans(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(select(PlanConfig).order_by(PlanConfig.sort_order))
    ).all()
    plans = [
        {
            "key": r.key,
            "price": r.price_cents / 100,
            "price_cents": r.price_cents,
            "token_budget": r.token_budget,
            "agents": r.agents,
            "rounds": r.rounds,
            "free_days": r.free_days,
            "stripe_price_id": r.stripe_price_id,
            "is_active": r.is_active,
        }
        for r in rows
    ]
    packs = (
        await db.scalars(select(CreditPack).order_by(CreditPack.sort_order))
    ).all()
    return {
        "plans": plans,
        "credit_packs": [
            {
                "key": p.key,
                "tokens": p.tokens,
                "price": p.price_cents / 100,
                "price_cents": p.price_cents,
                "stripe_price_id": p.stripe_price_id,
                "is_active": p.is_active,
            }
            for p in packs
        ],
    }


@router.put("/plans/{key}", dependencies=[Depends(admin_only)])
async def upsert_plan(key: str, data: PlanIn, db: AsyncSession = Depends(get_db)):
    if key not in {p["key"] for p in DEFAULT_PLANS}:
        raise HTTPException(status_code=400, detail="geçersiz plan anahtarı")
    row = await db.get(PlanConfig, key)
    if row is None:
        row = PlanConfig(key=key, sort_order=len(DEFAULT_PLANS))
    row.price_cents = round(data.price * 100)
    row.token_budget = data.token_budget
    row.agents = data.agents
    row.rounds = data.rounds
    row.free_days = data.free_days if key == "free" else 0
    row.stripe_price_id = data.stripe_price_id.strip()
    row.is_active = data.is_active
    db.add(row)
    await db.execute(
        update(User)
        .where(User.plan == key)
        .values(monthly_token_budget=data.token_budget)
    )
    await db.commit()
    return {"key": key, "saved": True}


@router.put("/credit-packs/{key}", dependencies=[Depends(admin_only)])
async def upsert_credit_pack(
    key: str, data: CreditPackIn, db: AsyncSession = Depends(get_db)
):
    if not key or len(key) > 32 or not all(c.isalnum() or c == "_" for c in key):
        raise HTTPException(status_code=400, detail="geçersiz paket anahtarı")
    row = await db.get(CreditPack, key)
    if row is None:
        row = CreditPack(key=key, sort_order=len(DEFAULT_PACKS))
    row.tokens = data.tokens
    row.price_cents = round(data.price * 100)
    row.stripe_price_id = data.stripe_price_id.strip()
    row.is_active = data.is_active
    db.add(row)
    await db.commit()
    return {"key": key, "saved": True}


@router.get("/users", dependencies=[Depends(admin_only)])
async def admin_users(
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    totals = (
        select(
            TokenUsage.user_id.label("uid"),
            func.coalesce(
                func.sum(TokenUsage.prompt_tokens + TokenUsage.completion_tokens), 0
            ).label("tokens"),
            func.coalesce(func.sum(TokenUsage.cost_usd), 0).label("cost"),
            func.count().label("calls"),
        )
        .group_by(TokenUsage.user_id)
        .subquery()
    )
    stmt = (
        select(User, totals.c.tokens, totals.c.cost, totals.c.calls)
        .outerjoin(totals, totals.c.uid == User.id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count()).select_from(User)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(User.email.ilike(pattern))
        count_stmt = count_stmt.where(User.email.ilike(pattern))
    rows = (await db.execute(stmt)).all()
    total = await db.scalar(count_stmt) or 0
    free_row = await db.get(PlanConfig, "free")
    free_days = free_row.free_days if free_row is not None else 0
    users = []
    for user, tokens, cost, calls in rows:
        users.append(
            {
                "id": str(user.id),
                "email": user.email,
                "plan": user.plan,
                "is_admin": user.is_admin,
                "billing_status": user.billing_status,
                "monthly_token_used": user.monthly_token_used or 0,
                "monthly_token_budget": user.monthly_token_budget or 0,
                "credit_balance": user.credit_balance or 0,
                "tokens_total": int(tokens or 0),
                "cost_total_usd": float(cost or 0),
                "calls_total": int(calls or 0),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "free_until": (
                    free_until(user.created_at, free_days).isoformat()
                    if user.plan == "free" and free_days > 0 and user.created_at
                    else None
                ),
                "free_expired": bool(
                    user.plan == "free"
                    and free_access_expired(user.created_at, free_days)
                ),
            }
        )
    return {"users": users, "total": total, "limit": limit, "offset": offset}


@router.get("/usage/summary", dependencies=[Depends(admin_only)])
async def usage_summary(db: AsyncSession = Depends(get_db)):
    calls, tokens, cost = (
        await db.execute(
            select(
                func.count(),
                func.coalesce(
                    func.sum(TokenUsage.prompt_tokens + TokenUsage.completion_tokens), 0
                ),
                func.coalesce(func.sum(TokenUsage.cost_usd), 0),
            )
        )
    ).one()
    return {
        "total_calls": int(calls or 0),
        "total_tokens": int(tokens or 0),
        "total_cost_usd": float(cost or 0),
    }


@router.get("/privacy/requests", dependencies=[Depends(admin_only)])
async def list_privacy_requests(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(PrivacyRequest).order_by(PrivacyRequest.requested_at.desc()).limit(50)
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "email": r.email,
            "status": r.status,
            "note": r.note,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]
