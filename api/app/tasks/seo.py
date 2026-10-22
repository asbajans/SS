"""Scheduled IndexNow submissions (sitemap ping + changed URLs)."""
from __future__ import annotations

import httpx
import structlog
from celery import shared_task
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import BlogPost, SeoSettings, SeoSubmission
from app.seo import abs_url, normalize_base_url

log = structlog.get_logger(__name__)


@shared_task(name="seo.indexnow")
def seo_indexnow() -> dict:
    """Submit the public URL set to IndexNow (no-op when disabled)."""
    import asyncio

    return asyncio.run(_submit())


async def _submit() -> dict:
    async with AsyncSessionLocal() as s:
        row = await s.get(SeoSettings, 1)
        if row is None or not row.indexnow_enabled or not row.indexnow_key:
            return {"skipped": True}
        base = normalize_base_url(row.site_url)
        posts = (
            await s.scalars(select(BlogPost).where(BlogPost.is_published.is_(True)))
        ).all()
        urls = [abs_url(base, "/"), abs_url(base, "/blog")]
        urls += [abs_url(base, f"/blog/{p.slug}") for p in posts]
        urls = list(dict.fromkeys(urls))

        body = {
            "host": base.split("://", 1)[-1].split("/")[0],
            "key": row.indexnow_key,
            "keyLocation": f"{base}/{row.indexnow_key}.txt",
            "urlList": urls,
        }
        endpoint = row.indexnow_endpoint or "https://api.indexnow.org/indexnow"
        status, detail = "failed", ""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(endpoint, json=body)
            status = "ok" if resp.status_code in (200, 202) else "failed"
            detail = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)[:200]

        s.add(
            SeoSubmission(
                url=",".join(urls[:5]) + (f" (+{len(urls) - 5} more)" if len(urls) > 5 else ""),
                status=status,
                detail=detail,
            )
        )
        await s.commit()
        log.info("indexnow_submitted", status=status, count=len(urls))
        return {"ok": status == "ok", "status": status, "count": len(urls), "detail": detail}
