"""Analytics event delivery endpoints.

- `GET  /api/analytics/events`   pending server-side events for the user
- `POST /api/analytics/events`   record a client-side event
- `POST /api/analytics/events/ack` mark events as delivered
- `GET  /api/admin/analytics/events` admin overview (recent events + counts)
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import admin_only
from app.analytics import normalize_name, record, serialize
from app.auth import current_user, get_db
from app.models import AnalyticsEvent, User

router = APIRouter(tags=["analytics"])


class ClientEventIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    params: dict = Field(default_factory=dict)
    value: float | None = None
    currency: str | None = Field(default=None, max_length=8)


class AckIn(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=200)


@router.get("/api/analytics/events")
async def pending_events(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Undelivered events for the current user (SPA forwards them to GA4)."""
    rows = (
        await db.scalars(
            select(AnalyticsEvent)
            .where(
                AnalyticsEvent.user_id == user.id,
                AnalyticsEvent.delivered_at.is_(None),
            )
            .order_by(AnalyticsEvent.created_at.asc())
            .limit(100)
        )
    ).all()
    return {"events": [serialize(e) for e in rows]}


@router.post("/api/analytics/events")
async def create_event(
    payload: ClientEventIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record a client-side activity (e.g. a click on a CTA)."""
    name = normalize_name(payload.name)
    if not name:
        raise HTTPException(status_code=400, detail="geçersiz olay adı")
    params = {k: v for k, v in (payload.params or {}).items() if isinstance(k, str)}
    event = await record(
        db,
        name,
        user_id=user.id,
        params=params,
        value=payload.value,
        currency=payload.currency,
        source="client",
    )
    await db.commit()
    return {"ok": True, "name": event.name if event else name}


@router.post("/api/analytics/events/ack")
async def ack_events(
    payload: AckIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark events as delivered to GA4."""
    if not payload.ids:
        return {"acked": 0}
    rows = (
        await db.scalars(
            select(AnalyticsEvent).where(
                AnalyticsEvent.user_id == user.id,
                AnalyticsEvent.id.in_(payload.ids),
            )
        )
    ).all()
    stamp = datetime.now(UTC)
    for row in rows:
        row.delivered_at = stamp
    await db.commit()
    return {"acked": len(rows)}


@router.get("/api/admin/analytics/events", dependencies=[Depends(admin_only)])
async def admin_events(
    limit: int = 100, db: AsyncSession = Depends(get_db)
) -> dict:
    """Recent analytics events + per-name counts (admin overview)."""
    limit = max(1, min(500, limit))
    rows = (
        await db.scalars(
            select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit)
        )
    ).all()
    counts = (
        await db.execute(
            select(AnalyticsEvent.name, func.count())
            .group_by(AnalyticsEvent.name)
            .order_by(func.count().desc())
        )
    ).all()
    return {
        "events": [
            {
                **serialize(e),
                "user_id": str(e.user_id) if e.user_id else None,
                "source": e.source,
                "delivered": e.delivered_at is not None,
            }
            for e in rows
        ],
        "counts": [{"name": name, "count": int(count)} for name, count in counts],
    }
