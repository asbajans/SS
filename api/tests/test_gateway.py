"""Gateway smoke test (offline, mock mode)."""

import pytest

from app.llm_gateway.config_resolver import TaskUnavailable
from app.llm_gateway.gateway import LLMGateway


class _FakeRateLimiter:
    async def acquire(self, *args, **kwargs):
        return None


class _FakeRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, ctx, result, task_key):
        self.calls.append((task_key, result))


class _FakeQuota:
    def __init__(self):
        self.checks = []

    async def __call__(self, task_key, est_prompt_tokens):
        self.checks.append((task_key, est_prompt_tokens))


class _FakeCfg:
    model = "mock"
    fallbacks = []
    max_tokens = 100
    temperature = 0.7
    rpm = 10
    tpm = 10_000
    daily_budget_tokens = 1_000_000
    monthly_budget_tokens = 1_000_000
    cost_in_usd_per_mtok = 0.0
    cost_out_usd_per_mtok = 0.0
    enabled = True


async def _resolve(task_key: str) -> _FakeCfg:
    return _FakeCfg()


async def test_gateway_mock_mode(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_mock_mode", True)
    recorder = _FakeRecorder()
    gw = LLMGateway(_resolve, _FakeRateLimiter(), recorder)
    res = await gw.call("agent_act", [{"role": "user", "content": "hi"}])
    assert res.status == "mock"
    assert res.prompt_tokens == 0 and res.completion_tokens == 0 and res.cost_usd == 0.0
    text = res.text
    assert "MOCK:agent_act" in text or '"action"' in text
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == "agent_act"


@pytest.mark.asyncio
async def test_gateway_unknown_task_rejected():
    async def disabled(task_key: str):
        raise TaskUnavailable("not configured")

    gw = LLMGateway(disabled, _FakeRateLimiter(), _FakeRecorder())
    with pytest.raises(TaskUnavailable):
        await gw.call("nope", [{"role": "user", "content": "x"}])
