"""Gateway smoke test (offline, mock mode)."""
from app.llm_gateway.gateway import LLMGateway


class _FakeRateLimiter:
    async def acquire(self, *args, **kwargs):
        return None


class _FakeRecorder:
    async def assert_quota(self, **kwargs):
        return None

    async def record(self, ctx, result, task_key):
        return None


class _FakeCfg:
    model = "mock"
    fallbacks = []
    max_tokens = 100
    temperature = 0.7
    rpm = 10


async def test_gateway_mock_mode():
    gw = LLMGateway(lambda task: _FakeCfg(), _FakeRateLimiter(), _FakeRecorder())
    res = await gw.call("agent_act", [{"role": "user", "content": "hi"}])
    assert "MOCK:agent_act" in res.text or '"action"' in res.text
