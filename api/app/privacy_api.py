"""DSR endpoints: request deletion of the authenticated user's account and data."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.models import PrivacyRequest, User
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.post("/requests", status_code=202)
async def create_deletion_request(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    existing = (
        await db.scalars(
            select(PrivacyRequest).where(
                PrivacyRequest.user_id == user.id,
                PrivacyRequest.status.in_(["pending", "processing"]),
            )
        )
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Bekleyen bir silme talebiniz zaten var")
    req = PrivacyRequest(user_id=user.id, email=user.email, status="pending")
    db.add(req)
    await db.commit()
    celery_app.send_task("privacy.delete_user", args=[str(user.id), str(req.id)])
    return {"request_id": str(req.id), "status": "pending"}


@router.get("/requests/mine")
async def my_requests(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(PrivacyRequest)
            .where(PrivacyRequest.user_id == user.id)
            .order_by(PrivacyRequest.requested_at.desc())
            .limit(10)
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "note": r.note,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        }
        for r in rows
    ]
