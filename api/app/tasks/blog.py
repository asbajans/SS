"""Celery tasks for the AI blog editor."""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from celery import shared_task
from sqlalchemy import select

from app.blog_editor import build_blog_messages, parse_generated_post, slugify
from app.config import settings
from app.db import AsyncSessionLocal
from app.llm_gateway.factory import build_gateway
from app.models import BlogAutomation, BlogPost, BlogTopic

log = structlog.get_logger(__name__)


async def _automation(s) -> BlogAutomation:
    row = await s.get(BlogAutomation, 1)
    if row is None:
        row = BlogAutomation(id=1, enabled=True, interval_days=7)
        s.add(row)
        await s.commit()
        await s.refresh(row)
    return row


async def _generate(topic_id: str) -> dict:
    redis_client = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with AsyncSessionLocal() as s:
            topic = await s.get(BlogTopic, UUID(str(topic_id)))
            if topic is None:
                return {"status": "missing"}
            if topic.status == "published":
                return {"status": "already_published"}
            topic.status = "generating"
            topic.error = None
            await s.commit()
            existing = (
                await s.scalars(
                    select(BlogPost.title_tr).order_by(BlogPost.published_at.desc()).limit(12)
                )
            ).all()
            gateway = build_gateway(s, redis_client, None)
            result = await gateway.call(
                "blog_editor",
                build_blog_messages(topic.topic, topic.keywords or "", list(existing)),
                response_json=True,
            )
            try:
                post = parse_generated_post(result.text, topic.topic)
            except ValueError as exc:
                topic.status = "failed"
                topic.error = str(exc)[:1000]
                await s.commit()
                return {"status": "failed", "error": str(exc)}

            base = slugify(post["title_tr"])
            slug = base
            suffix = 2
            while await s.get(BlogPost, slug) is not None:
                slug = f"{base[:110]}-{suffix}"
                suffix += 1
            now = datetime.now(UTC)
            s.add(
                BlogPost(
                    slug=slug,
                    title_tr=post["title_tr"],
                    title_en=post["title_en"],
                    excerpt_tr=post["excerpt_tr"],
                    excerpt_en=post["excerpt_en"],
                    body_tr=post["body_tr"],
                    body_en=post["body_en"],
                    is_published=True,
                    published_at=now,
                )
            )
            topic.status = "published"
            topic.post_slug = slug
            topic.published_at = now
            topic.error = None
            automation = await _automation(s)
            automation.last_run_at = now
            automation.next_run_at = now + timedelta(days=max(1, automation.interval_days))
            await s.commit()
            return {"status": "published", "slug": slug}
    except Exception as exc:  # noqa: BLE001
        log.exception("blog_generate_failed", topic_id=topic_id)
        async with AsyncSessionLocal() as s:
            topic = await s.get(BlogTopic, UUID(str(topic_id)))
            if topic is not None:
                topic.status = "failed"
                topic.error = str(exc)[:1000]
                await s.commit()
        return {"status": "failed", "error": str(exc)}
    finally:
        await redis_client.aclose()


async def _tick() -> dict:
    async with AsyncSessionLocal() as s:
        automation = await _automation(s)
        if not automation.enabled:
            return {"status": "disabled"}
        now = datetime.now(UTC)
        if automation.next_run_at is not None and automation.next_run_at > now:
            return {"status": "not_due"}
        topic = (
            await s.scalars(
                select(BlogTopic)
                .where(BlogTopic.status == "queued")
                .order_by(BlogTopic.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).first()
        if topic is None:
            return {"status": "empty"}
        topic.status = "scheduled"
        topic.scheduled_at = now
        automation.next_run_at = now + timedelta(days=max(1, automation.interval_days))
        await s.commit()
        topic_id = str(topic.id)
    from app.tasks.celery_app import celery_app

    celery_app.send_task("blog.generate_topic", args=[topic_id])
    return {"status": "queued", "topic_id": topic_id}


@shared_task(name="blog.generate_topic", max_retries=0)
def generate_topic(topic_id: str) -> dict:
    try:
        return asyncio.run(_generate(topic_id))
    except Exception as exc:  # noqa: BLE001
        log.exception("blog_task_failed", topic_id=topic_id)
        return {"status": "failed", "error": str(exc)}


@shared_task(name="blog.tick", max_retries=0)
def tick() -> dict:
    return asyncio.run(_tick())
