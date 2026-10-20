"""DB-backed per-task LLM configuration resolver with a short TTL cache.

Reads `model_configs` (admin CRUD via /api/admin/models). Results are cached
in memory for 30 s; admin upserts invalidate the cache so limit changes take
effect within seconds.
"""
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelConfig


@dataclass(frozen=True)
class TaskConfig:
    task_key: str
    model: str
    fallbacks: list[str]
    max_tokens: int
    temperature: float
    rpm: int
    tpm: int
    daily_budget_tokens: int
    monthly_budget_tokens: int
    cost_in_usd_per_mtok: float
    cost_out_usd_per_mtok: float
    enabled: bool


_TTL_SECONDS = 30.0
_CACHE: dict[str, tuple[float, TaskConfig]] = {}


class TaskUnavailable(Exception):
    """Requested task has no model config or is disabled."""


async def resolve_config(db: AsyncSession, task_key: str) -> TaskConfig:
    now = time.monotonic()
    hit = _CACHE.get(task_key)
    if hit is not None and hit[0] > now:
        return hit[1]

    row = (
        await db.scalars(select(ModelConfig).where(ModelConfig.task_key == task_key))
    ).first()
    if row is None or not row.enabled:
        raise TaskUnavailable(f"task {task_key!r} is not configured or disabled")

    cfg = TaskConfig(
        task_key=row.task_key,
        model=row.model,
        fallbacks=list(row.fallbacks or []),
        max_tokens=row.max_tokens,
        temperature=float(row.temperature),
        rpm=row.rpm,
        tpm=row.tpm,
        daily_budget_tokens=row.daily_budget_tokens,
        monthly_budget_tokens=row.monthly_budget_tokens,
        cost_in_usd_per_mtok=float(row.cost_in_usd_per_mtok or 0.0),
        cost_out_usd_per_mtok=float(row.cost_out_usd_per_mtok or 0.0),
        enabled=row.enabled,
    )
    _CACHE[task_key] = (now + _TTL_SECONDS, cfg)
    return cfg


def invalidate_config(task_key: str | None = None) -> None:
    if task_key is None:
        _CACHE.clear()
    else:
        _CACHE.pop(task_key, None)
