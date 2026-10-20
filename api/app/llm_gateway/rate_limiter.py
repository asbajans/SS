"""Redis token-bucket rate limiter.

One bucket per (task_key, dimension): ``rl:{task_key}:rpm`` (requests per
minute) and ``rl:{task_key}:tpm`` (tokens per minute). Atomic check-and-consume
via a Lua script so concurrent workers never over-spend.
"""
import time

import redis.asyncio as redis

_CONSUME_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_per_sec = tonumber(ARGV[3])
local consume = tonumber(ARGV[4])
local cur = redis.call('HMGET', key, 'tokens', 'updated_at')
local tokens = tonumber(cur[1])
local updated_at = tonumber(cur[2])
if tokens == nil then
    tokens = capacity
    updated_at = now
end
local elapsed = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + elapsed * refill_per_sec)
if tokens < consume then
    redis.call('HMSET', key, 'tokens', tokens, 'updated_at', now)
    redis.call('EXPIRE', key, 7200)
    return 0
end
tokens = tokens - consume
redis.call('HMSET', key, 'tokens', tokens, 'updated_at', now)
redis.call('EXPIRE', key, 7200)
return 1
"""


class RateLimitExceeded(Exception):
    """Rate limit (rpm/tpm) exceeded for a task."""


class TokenBucketLimiter:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    async def acquire(
        self,
        task_key: str,
        rpm: int,
        tpm: int,
        est_tokens: int = 0,
    ) -> None:
        now = time.time()
        allowed_rpm = await self.client.eval(
            _CONSUME_SCRIPT, 1, f"rl:{task_key}:rpm", now, rpm, rpm / 60.0, 1
        )
        allowed_tpm = await self.client.eval(
            _CONSUME_SCRIPT, 1, f"rl:{task_key}:tpm", now, tpm, tpm / 60.0, max(est_tokens, 1)
        )
        if not allowed_rpm or not allowed_tpm:
            raise RateLimitExceeded(f"rate limit exceeded for task {task_key!r}")
