"""Admin router: manage per-task model configs (model, quotas, fallbacks)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.llm_gateway.config_resolver import invalidate_config
from app.models import ModelConfig, TokenUsage

router = APIRouter(prefix="/api/admin", tags=["admin"])


def admin_only(user=Depends(current_user)) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")


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


@router.get("/usage/summary", dependencies=[Depends(admin_only)])
async def usage_summary(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(TokenUsage))).all()
    return {"total_calls": len(rows)}
