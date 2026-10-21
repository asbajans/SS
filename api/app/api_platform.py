"""Public API platform: keys, v1 endpoints and webhook management."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.models import ApiKey, Project, Run, Template, User, Webhook
from app.runs_api import (
    ProjectIn,
    _insights_payload,
    _plan_limits_or_402,
    _validate_sim_config,
)
from app.storage import get_bytes
from app.webhooks import EVENTS, validate_webhook_url

router = APIRouter(prefix="/api", tags=["platform"])
api_security = HTTPBearer(auto_error=False)


async def api_key_user(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(api_security),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw = request.headers.get("x-api-key") or (cred.credentials if cred else None)
    if not raw:
        raise HTTPException(status_code=401, detail="missing api key")
    digest = hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()
    key = (
        await db.scalars(
            select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.revoked_at.is_(None))
        )
    ).first()
    if key is None:
        raise HTTPException(status_code=401, detail="invalid api key")
    user = await db.get(User, key.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid api key")
    key.last_used_at = datetime.now(UTC)
    await db.commit()
    return user


class ApiKeyIn(BaseModel):
    name: str = "default"


class WebhookIn(BaseModel):
    url: str
    events: list[str] = ["run.completed", "run.failed"]


class WebhookPatch(BaseModel):
    active: bool


def _hook(row: Webhook) -> dict:
    return {
        "id": row.id,
        "url": row.url,
        "events": row.events or [],
        "active": row.active,
        "last_attempt_at": row.last_attempt_at.isoformat() if row.last_attempt_at else None,
        "last_status": row.last_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/api-keys")
async def list_api_keys(user=Depends(current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(
            select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
        )
    ).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.prefix,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "revoked": k.revoked_at is not None,
        }
        for k in rows
    ]


@router.post("/api-keys", status_code=201)
async def create_api_key(
    data: ApiKeyIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    active = (
        await db.scalars(
            select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None))
        )
    ).all()
    if len(active) >= 10:
        raise HTTPException(status_code=400, detail="en fazla 10 aktif API anahtarı")
    raw = "ss_live_" + secrets.token_urlsafe(32)
    key = ApiKey(
        user_id=user.id,
        name=(data.name or "default")[:120],
        prefix=raw[:14],
        key_hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )
    db.add(key)
    await db.commit()
    return {"id": key.id, "name": key.name, "key": raw, "prefix": key.prefix}


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    key = await db.get(ApiKey, key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    key.revoked_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=204)


@router.get("/webhooks")
async def list_webhooks(user=Depends(current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(
            select(Webhook).where(Webhook.user_id == user.id).order_by(Webhook.created_at.desc())
        )
    ).all()
    return [_hook(row) for row in rows]


@router.post("/webhooks", status_code=201)
async def create_webhook(
    data: WebhookIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        url = validate_webhook_url(data.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    events = [e for e in data.events if e in EVENTS]
    if not events:
        raise HTTPException(status_code=400, detail=f"events must contain one of {list(EVENTS)}")
    active = (await db.scalars(select(Webhook).where(Webhook.user_id == user.id))).all()
    if len(active) >= 5:
        raise HTTPException(status_code=400, detail="en fazla 5 webhook")
    secret = "whsec_" + secrets.token_urlsafe(24)
    hook = Webhook(user_id=user.id, url=url, secret=secret, events=events)
    db.add(hook)
    await db.commit()
    return {**_hook(hook), "secret": secret}


@router.patch("/webhooks/{hook_id}")
async def update_webhook(
    hook_id: uuid.UUID,
    data: WebhookPatch,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    hook = await db.get(Webhook, hook_id)
    if hook is None or hook.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    hook.active = data.active
    await db.commit()
    return _hook(hook)


@router.delete("/webhooks/{hook_id}", status_code=204)
async def delete_webhook(
    hook_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    hook = await db.get(Webhook, hook_id)
    if hook is None or hook.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(hook)
    await db.commit()
    return Response(status_code=204)


@router.get("/v1/me")
async def v1_me(user=Depends(api_key_user)) -> dict:
    return {"id": user.id, "email": user.email, "plan": user.plan}


@router.get("/v1/templates")
async def v1_templates(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(
            select(Template).where(Template.is_active.is_(True)).order_by(Template.key)
        )
    ).all()
    return [
        {"key": t.key, "name": t.name, "description": t.description}
        for t in rows
    ]


@router.get("/v1/projects")
async def v1_projects(user=Depends(api_key_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(
            select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
        )
    ).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "template_key": p.template_key,
            "language": p.language,
            "sim_config": p.sim_config,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]


@router.post("/v1/projects", status_code=201)
async def v1_create_project(
    data: ProjectIn, user=Depends(api_key_user), db: AsyncSession = Depends(get_db)
) -> dict:
    tpl = await db.get(Template, data.template_key)
    if tpl is None or not tpl.is_active:
        raise HTTPException(status_code=400, detail=f"unknown template: {data.template_key}")
    limits = await _plan_limits_or_402(db, user)
    defaults = (tpl.pack or {}).get("sim_defaults") or {}
    invalid = _validate_sim_config(data.sim_config, limits, defaults, data.template_key)
    if invalid:
        raise HTTPException(status_code=400, detail=invalid)
    project = Project(
        user_id=user.id,
        name=data.name,
        template_key=data.template_key,
        language=data.language,
        sim_config=data.sim_config,
    )
    db.add(project)
    await db.commit()
    return {"id": project.id, "status": project.status, "template_key": project.template_key}


@router.post("/v1/projects/{project_id}/runs", status_code=202)
async def v1_create_run(
    project_id: uuid.UUID, user=Depends(api_key_user), db: AsyncSession = Depends(get_db)
) -> dict:
    project = (
        await db.scalars(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="not found")
    limits = await _plan_limits_or_402(db, user)
    tpl = await db.get(Template, project.template_key)
    defaults = (tpl.pack or {}).get("sim_defaults") if tpl is not None else {}
    invalid = _validate_sim_config(
        project.sim_config or {}, limits, defaults or {}, project.template_key
    )
    if invalid:
        raise HTTPException(status_code=400, detail=invalid)
    run = Run(project_id=project.id, sim_config=project.sim_config)
    db.add(run)
    await db.commit()
    from app.tasks.celery_app import celery_app

    celery_app.send_task("pipeline.run", args=[str(run.id)], task_id=str(uuid.uuid4()))
    return {"run_id": run.id, "queued": True}


@router.get("/v1/runs")
async def v1_runs(user=Depends(api_key_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(
            select(Run)
            .join(Project, Run.project_id == Project.id)
            .where(Project.user_id == user.id)
            .order_by(Run.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "status": r.status,
            "current_round": r.current_round,
            "tokens_used": r.tokens_used,
            "report_ready": bool(r.report_object_key),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in rows
    ]


async def _owned_run(db: AsyncSession, user: User, run_id: uuid.UUID) -> Run:
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="not found")
    project = await db.get(Project, run.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    return run


@router.get("/v1/runs/{run_id}")
async def v1_run(
    run_id: uuid.UUID, user=Depends(api_key_user), db: AsyncSession = Depends(get_db)
) -> dict:
    run = await _owned_run(db, user, run_id)
    return {
        "id": run.id,
        "project_id": run.project_id,
        "status": run.status,
        "current_round": run.current_round,
        "tokens_used": run.tokens_used,
        "error": run.error,
        "report_ready": bool(run.report_object_key),
        "report_meta": run.report_meta,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("/v1/runs/{run_id}/insights")
async def v1_run_insights(
    run_id: uuid.UUID, user=Depends(api_key_user), db: AsyncSession = Depends(get_db)
) -> dict:
    run = await _owned_run(db, user, run_id)
    project = await db.get(Project, run.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="not found")
    return await _insights_payload(db, run, project)


@router.get("/v1/runs/{run_id}/report/download")
async def v1_download_report(
    run_id: uuid.UUID,
    format: str = "pdf",
    user=Depends(api_key_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    run = await _owned_run(db, user, run_id)
    meta = run.report_meta or {}
    if format == "md":
        key = meta.get("md_key")
        media_type = "text/markdown; charset=utf-8"
        ext = "md"
    else:
        key = run.report_object_key
        media_type = "application/pdf"
        ext = "pdf"
    if not key:
        raise HTTPException(status_code=404, detail="report not ready")
    data = await get_bytes(key)
    filename = f"simulasyon-raporu-{str(run.id)[:8]}.{ext}"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
