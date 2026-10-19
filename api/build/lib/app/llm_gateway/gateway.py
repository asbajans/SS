"""LLM Gateway: task-based model routing, quotas, rate limits, fallbacks, usage ledger.

The ONLY external network call in the whole system happens here (OpenRouter),
unless llm_mock_mode is enabled (CI/dev) or an empty API key forces mock mode.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

TASK_KEYS = [
    "ingest_ontology",
    "persona_synth",
    "agent_act",
    "agent_digest",
    "analyst_draft",
    "report_outline",
    "report_section",
    "agent_interview",
]


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    status: str  # ok | fallback | failed
    fallback_used: str | None = None


class QuotaExceeded(Exception):
    pass


class LLMGateway:
    """Single choke point for all LLM traffic.

    - resolves per-task config (model, max_tokens, temperature, rpm, budgets)
    - enforces max_tokens (no unbounded generations)
    - Redis token-bucket rate limiter
    - fallback chain
    - usage accounting -> token_usage rows (via Injection of a callback)
    """

    def __init__(self, config_resolver, rate_limiter, usage_recorder) -> None:
        self.config_resolver = config_resolver
        self.rate_limiter = rate_limiter
        self.usage_recorder = usage_recorder

    def _mock_result(self, task_key: str) -> LLMResult:
        payload = (
            "MOCK:" + task_key if task_key != "agent_act" else json.dumps(
                {"action": "post", "content": "Mock content", "emotion": "neutral"}
            )
        )
        return LLMResult(payload, "mock", 0, 0, 0.0, "mock")

    async def call(
        self,
        task_key: str,
        messages: list[dict[str, str]],
        *,
        user_id: str | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        response_json: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> LLMResult:
        if settings.llm_mock_mode or not settings.openrouter_api_key:
            return self._mock_result(task_key)

        cfg = await self.config_resolver(task_key)  # excludes disabled tasks
        await self.rate_limiter.acquire(task_key, cfg.rpm, cfg.tpm)

        # verify quotas before spending: run budget, user monthly budget, task daily budget
        await self.usage_recorder.assert_quota(
            user_id=user_id, task_key=task_key, est_prompt_tokens=self._est_tokens(messages)
        )

        candidates = [cfg.model, *cfg.fallbacks]
        last_exc: BaseException | None = None
        for model in candidates:
            body: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": cfg.max_tokens,  # mandatory cap
                "temperature": float(cfg.temperature),
                "usage": {"include": True},  # OpenRouter accounting
            }
            if response_json:
                body["response_format"] = {"type": "json_object"}
            if extra:
                body.update(extra)

            started = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=180) as client:  # noqa: S113
                    r = await client.post(
                        f"{settings.openrouter_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.openrouter_api_key}",
                            "HTTP-Referer": "https://app.example.com",
                            "X-Title": "CrowdScope",
                        },
                        json=body,
                    )
                    r.raise_for_status()
                    data = r.json()
            except BaseException as e:  # noqa: S112
                last_exc = e
                log.warning("llm_call_failed", model=model, task=task_key, err=str(e))
                continue

            choice = data["choices"][0]
            usage = data.get("usage", {})
            result = LLMResult(
                text=choice["message"]["content"],
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                cost_usd=float(usage.get("cost", 0.0) or 0.0),
                status="ok",
            )
            if model != cfg.model:
                result.status = "fallback"
                result.fallback_used = model

            await self.usage_recorder.record(self._ctx(locals()), result, task_key)
            log.info(
                "llm_call",
                task=task_key,
                model=model,
                pt=result.prompt_tokens,
                ct=result.completion_tokens,
                cost=result.cost_usd,
                dt=round(time.monotonic() - started, 2),
            )
            return result

        raise RuntimeError(f"All LLM candidates failed for task={task_key}: {last_exc}")

    def _ctx(self, local_vars: dict) -> dict:
        return {
            k: local_vars.get(k)
            for k in ("user_id", "project_id", "run_id", "agent_id")
        }
