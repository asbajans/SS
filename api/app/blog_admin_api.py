"""Admin endpoints for the AI blog editor."""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import admin_only
from app.auth import get_db
from app.models import BlogAutomation, BlogPost, BlogTopic
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/admin/blog", tags=["admin-blog"])


def _topic(topic: BlogTopic) -> dict:
    return {
        "id": str(topic.id),
        "topic": topic.topic,
        "keywords": topic.keywords,
        "status": topic.status,
        "post_slug": topic.post_slug,
        "scheduled_at": topic.scheduled_at.isoformat() if topic.scheduled_at else None,
        "published_at": topic.published_at.isoformat() if topic.published_at else None,
        "error": topic.error,
        "created_at": topic.created_at.isoformat() if topic.created_at else None,
    }


def _automation(row: BlogAutomation) -> dict:
    return {
        "enabled": row.enabled,
        "interval_days": row.interval_days,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
    }


async def _automation_row(db: AsyncSession) -> BlogAutomation:
    row = await db.get(BlogAutomation, 1)
    if row is None:
        row = BlogAutomation(id=1, enabled=True, interval_days=7)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def _dispatch(task: str, *args) -> None:
    try:
        celery_app.send_task(task, args=list(args))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="task queue unavailable") from exc


class TopicIn(BaseModel):
    topic: str = Field(min_length=4, max_length=200)
    keywords: str = Field(default="", max_length=400)


class BulkTopicsIn(BaseModel):
    topics: list[TopicIn] = Field(min_length=1, max_length=50)


class AutomationIn(BaseModel):
    enabled: bool = True
    interval_days: int = Field(default=7, ge=1, le=365)


class PostIn(BaseModel):
    is_published: bool


@router.get("/topics", dependencies=[Depends(admin_only)])
async def list_topics(status: str | None = None, db: AsyncSession = Depends(get_db)) -> list[dict]:
    query = select(BlogTopic).order_by(BlogTopic.created_at.desc()).limit(300)
    if status:
        query = query.where(BlogTopic.status == status)
    return [_topic(row) for row in (await db.scalars(query)).all()]


@router.post("/topics", dependencies=[Depends(admin_only)])
async def add_topics(payload: BulkTopicsIn, db: AsyncSession = Depends(get_db)) -> dict:
    added = 0
    seen: set[str] = set()
    for item in payload.topics:
        topic = item.topic.strip()
        key = topic.casefold()
        if len(topic) < 4 or key in seen:
            continue
        seen.add(key)
        db.add(BlogTopic(topic=topic, keywords=item.keywords.strip(), status="queued"))
        added += 1
    await db.commit()
    automation = await _automation_row(db)
    if added and automation.enabled:
        automation.next_run_at = datetime.now(UTC)
        await db.commit()
        _dispatch("blog.tick")
    return {"added": added}


@router.delete("/topics/{topic_id}", dependencies=[Depends(admin_only)])
async def delete_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    topic = await db.get(BlogTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    if topic.status == "generating":
        raise HTTPException(status_code=409, detail="topic is generating")
    await db.delete(topic)
    await db.commit()
    return {"ok": True}


@router.post("/topics/{topic_id}/generate", dependencies=[Depends(admin_only)])
async def generate_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    topic = await db.get(BlogTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="topic not found")
    if topic.status in {"published", "generating"}:
        raise HTTPException(status_code=409, detail="topic already used")
    topic.status = "scheduled"
    topic.scheduled_at = datetime.now(UTC)
    topic.error = None
    await db.commit()
    _dispatch("blog.generate_topic", str(topic_id))
    return {"ok": True, "status": "scheduled"}


@router.get("/automation", dependencies=[Depends(admin_only)])
async def get_automation(db: AsyncSession = Depends(get_db)) -> dict:
    return _automation(await _automation_row(db))


@router.put("/automation", dependencies=[Depends(admin_only)])
async def put_automation(payload: AutomationIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _automation_row(db)
    now = datetime.now(UTC)
    if payload.enabled and (not row.enabled or row.next_run_at is None):
        row.next_run_at = now
    if not payload.enabled:
        row.next_run_at = None
    row.enabled = payload.enabled
    row.interval_days = payload.interval_days
    await db.commit()
    await db.refresh(row)
    if row.enabled:
        _dispatch("blog.tick")
    return _automation(row)


@router.post("/tick", dependencies=[Depends(admin_only)])
async def run_tick() -> dict:
    _dispatch("blog.tick")
    return {"ok": True}


@router.get("/posts", dependencies=[Depends(admin_only)])
async def list_posts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(select(BlogPost).order_by(BlogPost.published_at.desc()).limit(300))
    ).all()
    return [
        {
            "slug": row.slug,
            "title_tr": row.title_tr,
            "title_en": row.title_en,
            "is_published": row.is_published,
            "published_at": row.published_at.isoformat() if row.published_at else None,
        }
        for row in rows
    ]


@router.patch("/posts/{slug}", dependencies=[Depends(admin_only)])
async def update_post(slug: str, payload: PostIn, db: AsyncSession = Depends(get_db)) -> dict:
    post = await db.get(BlogPost, slug)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    post.is_published = payload.is_published
    if payload.is_published and post.published_at is None:
        post.published_at = datetime.now(UTC)
    await db.commit()
    return {"ok": True, "is_published": post.is_published}
