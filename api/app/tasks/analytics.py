"""Periodic GA4 delivery of queued analytics events (server-side)."""
from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

from app.analytics import dispatch_pending
from app.db import AsyncSessionLocal

log = structlog.get_logger(__name__)


@shared_task(name="analytics.dispatch")
def analytics_dispatch() -> dict:
    """Flush pending analytics events to GA4 via the Measurement Protocol."""

    async def run() -> dict:
        async with AsyncSessionLocal() as s:
            return await dispatch_pending(s)

    try:
        result = asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        log.warning("analytics_dispatch_failed", error=str(exc)[:200])
        return {"ok": False, "error": str(exc)[:200]}
    if result.get("sent"):
        log.info("analytics_dispatched", sent=result["sent"])
    return result
