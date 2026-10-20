"""DSR: user account + data deletion (Celery task)."""
import asyncio
from datetime import UTC, datetime

import structlog
from celery import shared_task
from sqlalchemy import delete, or_, select, update

from app.db import AsyncSessionLocal
from app.models import (
    Agent,
    Document,
    DocumentChunk,
    Ontology,
    PrivacyRequest,
    Project,
    Run,
    RunEvent,
    TokenUsage,
    User,
)
from app.storage import delete_prefix

log = structlog.get_logger(__name__)


@shared_task(name="privacy.delete_user", max_retries=2)
def delete_user(user_id: str, request_id: str) -> dict:
    return asyncio.run(_delete_user(user_id, request_id))


async def _delete_user(user_id: str, request_id: str) -> dict:
    async with AsyncSessionLocal() as s:
        req = await s.get(PrivacyRequest, request_id)
        if req is not None:
            req.status = "processing"
            await s.commit()
        try:
            project_ids = (
                await s.scalars(select(Project.id).where(Project.user_id == user_id))
            ).all()
            for pid in project_ids:
                await delete_prefix(f"projects/{pid}/")
            run_ids = (
                await s.scalars(select(Run.id).where(Run.project_id.in_(project_ids)))
            ).all() if project_ids else []
            if run_ids:
                await s.execute(delete(RunEvent).where(RunEvent.run_id.in_(run_ids)))
            await s.execute(
                update(TokenUsage)
                .where(
                    or_(
                        TokenUsage.user_id == user_id,
                        TokenUsage.project_id.in_(project_ids) if project_ids else False,
                    )
                )
                .values(user_id=None, project_id=None, run_id=None, agent_id=None)
            )
            if project_ids:
                await s.execute(delete(Agent).where(Agent.project_id.in_(project_ids)))
                await s.execute(delete(Ontology).where(Ontology.project_id.in_(project_ids)))
                await s.execute(
                    delete(DocumentChunk).where(DocumentChunk.project_id.in_(project_ids))
                )
                await s.execute(delete(Document).where(Document.project_id.in_(project_ids)))
                await s.execute(delete(Run).where(Run.project_id.in_(project_ids)))
                await s.execute(delete(Project).where(Project.id.in_(project_ids)))
            user = await s.get(User, user_id)
            if user is not None:
                await s.delete(user)
            if req is not None:
                req.status = "completed"
                req.processed_at = datetime.now(UTC)
                req.user_id = None
                req.email = None
            await s.commit()
            log.info("privacy_deletion_completed", user_id=user_id, projects=len(project_ids))
            return {"status": "completed", "projects": len(project_ids)}
        except Exception as exc:  # noqa: BLE001
            await s.rollback()
            if req is not None:
                req = await s.get(PrivacyRequest, request_id)
                if req is not None:
                    req.status = "failed"
                    req.note = str(exc)[:500]
                    req.processed_at = datetime.now(UTC)
                    await s.commit()
            log.error("privacy_deletion_failed", user_id=user_id, err=str(exc))
            raise
