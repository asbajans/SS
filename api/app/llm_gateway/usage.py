"""Usage ledger + quota guards.

Writes every LLM call to `token_usage` and updates the user's monthly token
counter. Quotas are checked *before* a call spends anything.
"""
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm_gateway.config_resolver import resolve_config
from app.models import TokenUsage, User


class QuotaExceeded(Exception):
    """A user or task quota would be exceeded."""


async def record_usage(
    db: AsyncSession,
    ctx: dict,
    result,
    task_key: str,
    user_id=None,
) -> None:
    row = TokenUsage(
        user_id=user_id,
        project_id=ctx.get("project_id"),
        run_id=ctx.get("run_id"),
        agent_id=ctx.get("agent_id"),
        task_key=task_key,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        status=result.status,
        meta={"fallback_used": result.fallback_used},
    )
    db.add(row)
    await db.flush()

    if user_id is not None:
        user = await db.get(User, user_id)
        if user is not None:
            user.monthly_token_used = (user.monthly_token_used or 0) + (
                result.prompt_tokens + result.completion_tokens
            )
            db.add(user)

    await db.commit()


async def assert_quota(
    db: AsyncSession,
    user_id,
    task_key: str,
    est_prompt_tokens: int,
) -> None:
    if user_id is not None:
        user = await db.get(User, user_id)
        if (
            user is not None
            and user.monthly_token_budget is not None
            and (user.monthly_token_used or 0) + est_prompt_tokens
            > user.monthly_token_budget
        ):
            raise QuotaExceeded("monthly token budget exceeded")

    cfg = await resolve_config(db, task_key)
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = (
        await db.scalars(
            select(func.coalesce(func.sum(TokenUsage.prompt_tokens + TokenUsage.completion_tokens), 0)).where(
                TokenUsage.task_key == task_key
            ).where(TokenUsage.created_at >= today_start)
        )
    ).first() or 0
    if (used or 0) + est_prompt_tokens > cfg.daily_budget_tokens:
        raise QuotaExceeded("task daily token budget exceeded")

    # Account-level OpenRouter spend cap (soft signal; hard cap lives in OpenRouter).
    total_cost = (
        await db.scalars(select(func.coalesce(func.sum(TokenUsage.cost_usd), 0)))
    ).first() or 0.0
    if settings.openrouter_monthly_cap_usd and total_cost > settings.openrouter_monthly_cap_usd:
        raise QuotaExceeded("account monthly cost cap exceeded")
