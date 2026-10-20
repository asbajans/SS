"""Project document uploads + listing (MinIO-backed)."""
import hashlib
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import storage
from app.auth import current_user, get_db
from app.models import Document, DocumentChunk, Project

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024
ALLOWED_EXT = {".txt", ".md", ".pdf"}


async def _owned_project(db: AsyncSession, user, project_id: str) -> Project:
    project = (
        await db.scalars(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="not found")
    return project


@router.post("/projects/{project_id}/documents", status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _owned_project(db, user, project_id)
    filename = Path(file.filename or "upload.txt").name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="only .txt, .md and .pdf are supported")
    data = await file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 20MB)")

    key = f"projects/{project.id}/docs/{uuid.uuid4().hex}{ext}"
    await storage.put_bytes(key, data, file.content_type or "application/octet-stream")
    doc = Document(
        project_id=project.id,
        filename=filename,
        minio_key=key,
        mime=file.content_type,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(doc)
    await db.commit()

    from app.tasks.celery_app import celery_app

    celery_app.send_task("ingest.document", args=[str(doc.id)])
    return {"id": doc.id, "filename": doc.filename, "size": doc.size, "status": "queued"}


@router.get("/projects/{project_id}/documents")
async def list_documents(
    project_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)
):
    project = await _owned_project(db, user, project_id)
    rows = (
        await db.execute(
            select(Document, func.count(DocumentChunk.id))
            .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
            .where(Document.project_id == project.id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        )
    ).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "mime": doc.mime,
            "size": doc.size,
            "chunks": chunks,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc, chunks in rows
    ]


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)
):
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="not found")
    project = await db.get(Project, doc.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    try:
        await storage.delete_object(doc.minio_key)
    except Exception as exc:  # noqa: BLE001
        log.warning("minio_delete_failed", key=doc.minio_key, err=str(exc))
    await db.delete(doc)
    await db.commit()
    return {"deleted": True}
