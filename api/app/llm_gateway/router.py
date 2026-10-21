"""LLM Gateway HTTP router.

POST /api/llm/chat/completions  - task-routed completion with quotas, rate
limits, fallbacks and usage accounting.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import current_user, get_db
from app.config import settings
from app.llm_gateway.config_resolver import TaskUnavailable, resolve_config
from app.llm_gateway.gateway import LLMGateway
from app.llm_gateway.rate_limiter import RateLimitExceeded, TokenBucketLimiter
from app.llm_gateway.usage import QuotaExceeded as QuotaExceededUsage
from app.llm_gateway.usage import assert_quota, record_usage
from app.models import User

router = APIRouter(prefix="/api/llm", tags=["llm"])


class ChatIn(BaseModel):
    task_key: str
    messages: list[dict[str, str]]
    response_json: bool = False


class ChatOut(BaseModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    status: str
    fallback_used: str | None = None


def _redis() -> Any:
    import redis.asyncio as redis

    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@router.post("/chat/completions", response_model=ChatOut)
async def chat_completions(
    body: ChatIn,
    user: User = Depends(current_user),
    db=Depends(get_db),
) -> ChatOut:
    redis_client = _redis()
    try:
        gateway = LLMGateway(
            config_resolver=lambda tk: resolve_config(db, tk),
            rate_limiter=TokenBucketLimiter(redis_client),
            usage_recorder=lambda ctx, result, tk: record_usage(
                db, ctx, result, tk, user_id=user.id
            ),
            quota_checker=lambda tk, est: assert_quota(db, user.id, tk, est),
        )

        result = await gateway.call(
            body.task_key,
            body.messages,
            user_id=str(user.id),
            project_id=None,
            run_id=None,
            agent_id=None,
            response_json=body.response_json,
        )
        return ChatOut(
            text=result.text,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            status=result.status,
            fallback_used=result.fallback_used,
        )
    except TaskUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (QuotaExceededUsage, RateLimitExceeded) as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from None
    except Exception as exc:  # noqa: BLE001 - all providers failed
        raise HTTPException(status_code=502, detail=f"LLM unavailable: {exc}") from exc
    finally:
        await redis_client.aclose()


@router.get("/configs/{task_key}")
async def task_config(task_key: str, db=Depends(get_db)):
    cfg = await resolve_config(db, task_key)
    return {
        "task_key": cfg.task_key,
        "model": cfg.model,
        "fallbacks": cfg.fallbacks,
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
        "rpm": cfg.rpm,
        "tpm": cfg.tpm,
        "enabled": cfg.enabled,
    }
