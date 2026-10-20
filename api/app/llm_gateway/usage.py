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


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def credit_debit(before: int, after: int, budget: int, balance: int) -> int:
    overflow = max(0, after - budget) - max(0, before - budget)
    if overflow <= 0 or balance <= 0:
        return 0
    return min(overflow, balance)


def _reset_usage_if_needed(user: User) -> None:
    if user.plan != "free":
        return
    now = datetime.now(UTC)
    if user.usage_period_start is None or user.usage_period_start < _month_start(now):
        user.monthly_token_used = 0
        user.usage_period_start = now


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
            _reset_usage_if_needed(user)
            before = user.monthly_token_used or 0
            tokens = result.prompt_tokens + result.completion_tokens
            after = before + tokens
            user.monthly_token_used = after
            budget = user.monthly_token_budget or 0
            debit = credit_debit(before, after, budget, user.credit_balance or 0)
            if debit > 0:
                user.credit_balance = (user.credit_balance or 0) - debit
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
        if user is not None:
            _reset_usage_if_needed(user)
            budget = user.monthly_token_budget
            if (
                budget is not None
                and (user.monthly_token_used or 0) + est_prompt_tokens > budget
                and (user.credit_balance or 0) <= 0
            ):
                raise QuotaExceeded("monthly token budget exceeded; kredi yükleyin")

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
