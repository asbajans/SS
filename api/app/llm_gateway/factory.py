"""Gateway factory bound to a database session (API + workers share this)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm_gateway.config_resolver import resolve_config
from app.llm_gateway.gateway import LLMGateway
from app.llm_gateway.rate_limiter import TokenBucketLimiter
from app.llm_gateway.usage import assert_quota, record_usage


def build_gateway(
    db: AsyncSession,
    redis_client,
    user_id,
    project_id=None,
    run_id=None,
    agent_id=None,
) -> LLMGateway:
    async def _record(ctx, result, task_key):
        await record_usage(db, ctx, result, task_key, user_id=user_id)

    async def _quota(task_key: str, est_prompt_tokens: int):
        await assert_quota(db, user_id, task_key, est_prompt_tokens)

    return LLMGateway(
        config_resolver=lambda task_key: resolve_config(db, task_key),
        rate_limiter=TokenBucketLimiter(redis_client),
        usage_recorder=_record,
        quota_checker=_quota,
    )
