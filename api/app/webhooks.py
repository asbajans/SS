"""Outbound webhook validation and delivery."""
import asyncio
import hashlib
import hmac
import ipaddress
import json
import socket
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
import structlog
from celery import shared_task
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Project, Run, Webhook

log = structlog.get_logger(__name__)

EVENTS = ("run.completed", "run.failed")


def validate_webhook_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("webhook url must be a valid https url")
    if parsed.username or parsed.password:
        raise ValueError("credentials are not allowed in webhook url")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ValueError("private webhook hosts are not allowed")
    return url


def assert_public_host(host: str) -> None:
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not infos:
        raise ValueError("webhook host did not resolve")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("private webhook address is not allowed")


async def dispatch_run_event(run_id: str, event: str) -> None:
    async with AsyncSessionLocal() as s:
        run = await s.get(Run, run_id)
        if run is None:
            return
        project = await s.get(Project, run.project_id)
        if project is None:
            return
        hooks = (
            await s.scalars(
                select(Webhook).where(
                    Webhook.user_id == project.user_id, Webhook.active.is_(True)
                )
            )
        ).all()
        payload = {
            "event": event,
            "run_id": str(run.id),
            "project_id": str(project.id),
            "project_name": project.name,
            "status": run.status,
            "report_ready": bool(run.report_object_key),
            "tokens_used": run.tokens_used,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    targets = [str(h.id) for h in hooks if event in (h.events or [])]
    if not targets:
        return
    from app.tasks.celery_app import celery_app

    for hook_id in targets:
        celery_app.send_task(
            "webhooks.deliver", args=[hook_id, payload], task_id=str(uuid.uuid4())
        )


async def _deliver(webhook_id: str, payload: dict) -> dict:
    async with AsyncSessionLocal() as s:
        hook = await s.get(Webhook, webhook_id)
        if hook is None or not hook.active:
            return {"status": "skipped"}
        url, secret = hook.url, hook.secret
        hook.last_attempt_at = datetime.now(UTC)
        await s.commit()

    host = urlparse(url).hostname
    if host is None:
        raise ValueError("invalid webhook url")
    assert_public_host(host)

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        resp = await client.post(
            url,
            content=body,
            headers={
                "content-type": "application/json",
                "user-agent": "SocialSimulation-Webhook/1.0",
                "x-ss-event": str(payload.get("event", "")),
                "x-ss-signature": f"sha256={signature}",
            },
        )
    if resp.status_code >= 300:
        raise RuntimeError(f"webhook responded {resp.status_code}")

    async with AsyncSessionLocal() as s:
        hook = await s.get(Webhook, webhook_id)
        if hook is not None:
            hook.last_status = str(resp.status_code)
            await s.commit()
    return {"status": "ok", "code": resp.status_code}


async def _mark_error(webhook_id: str, error: str) -> None:
    async with AsyncSessionLocal() as s:
        hook = await s.get(Webhook, webhook_id)
        if hook is not None:
            hook.last_status = f"error: {error[:200]}"
            await s.commit()


@shared_task(bind=True, name="webhooks.deliver", max_retries=2)
def deliver(self, webhook_id: str, payload: dict) -> dict:
    try:
        return asyncio.run(_deliver(webhook_id, payload))
    except Exception as exc:  # noqa: BLE001
        log.warning("webhook_delivery_failed", webhook_id=webhook_id, err=str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1)) from exc
        asyncio.run(_mark_error(webhook_id, str(exc)))
        return {"status": "failed", "error": str(exc)}
