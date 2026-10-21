"""Runs router (thick logic lives in Celery pipeline; see agent.md s8)."""
import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.db import AsyncSessionLocal
from app.models import Agent, Ontology, Project, Run, RunEvent, Template
from app.plans import free_access_expired, get_plan_limits
from app.storage import get_bytes
from engine.insights import build_run_insights

router = APIRouter(prefix="/api")

ACTIVE_STATUSES = {"pending", "ingesting", "ontology", "population", "running", "report"}
TERMINAL_STATUSES = {"completed", "failed", "canceled"}


def _validate_sim_config(
    cfg: dict,
    limits: dict,
    defaults: dict | None = None,
    template_key: str | None = None,
) -> str | None:
    defaults = defaults or {}
    if template_key == "social_post_test":
        post_text = str(cfg.get("post_text") or "").strip()
        if len(post_text) < 10:
            return "social_post_test için en az 10 karakterlik post_text gerekli"
        if len(post_text) > 4000:
            return "post_text en fazla 4000 karakter olabilir"
    agents_n = cfg.get("agents_n", defaults.get("agents_n", 60))
    if not isinstance(agents_n, int) or isinstance(agents_n, bool) or not (
        1 <= agents_n <= limits["agents"]
    ):
        return (
            f"agents_n must be an integer between 1 and {limits['agents']} "
            f"for the {limits['plan']} plan"
        )
    rounds = cfg.get("rounds", defaults.get("rounds", 20))
    if not isinstance(rounds, int) or isinstance(rounds, bool) or not (
        1 <= rounds <= limits["rounds"]
    ):
        return (
            f"rounds must be an integer between 1 and {limits['rounds']} "
            f"for the {limits['plan']} plan"
        )
    return None


class ProjectIn(BaseModel):
    name: str
    template_key: str = "market_research"
    language: str = "tr"
    sim_config: dict = {}


@router.get("/projects")
async def list_projects(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
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
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]


async def _plan_limits_or_402(db: AsyncSession, user) -> dict:
    limits = await get_plan_limits(db, user.plan)
    if (
        user.plan == "free"
        and free_access_expired(user.created_at, limits["free_days"])
        and (user.credit_balance or 0) <= 0
    ):
        raise HTTPException(
            status_code=402,
            detail="Ücretsiz dönem sona erdi; planınızı yükseltin veya kredi yükleyin",
        )
    return limits


@router.post("/projects", status_code=201)
async def create_project(data: ProjectIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    template_key = data.template_key
    tpl = await db.get(Template, template_key)
    if tpl is None or not tpl.is_active:
        raise HTTPException(status_code=400, detail=f"unknown template: {template_key}")
    limits = await _plan_limits_or_402(db, user)
    defaults = (tpl.pack or {}).get("sim_defaults") or {}
    invalid = _validate_sim_config(data.sim_config, limits, defaults, template_key)
    if invalid:
        raise HTTPException(status_code=400, detail=invalid)
    project = Project(
        user_id=user.id,
        name=data.name,
        template_key=template_key,
        language=data.language,
        sim_config=data.sim_config,
    )
    db.add(project)
    await db.commit()
    return {"id": project.id, "status": project.status, "template_key": project.template_key}


@router.post("/projects/{project_id}/runs", status_code=202)
async def create_run(project_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
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


@router.get("/runs")
async def list_runs(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(Run)
            .join(Project, Run.project_id == Project.id)
            .where(Project.user_id == user.id)
            .order_by(Run.created_at.desc())
        )
    ).all()
    ids = {r.project_id for r in rows}
    projects = {
        p.id: p
        for p in (await db.scalars(select(Project).where(Project.id.in_(ids)))).all()
    }
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "project_name": projects[r.project_id].name if r.project_id in projects else None,
            "template_key": (
                projects[r.project_id].template_key if r.project_id in projects else None
            ),
            "language": projects[r.project_id].language if r.project_id in projects else "tr",
            "status": r.status,
            "current_round": r.current_round,
            "tokens_used": r.tokens_used,
            "report_ready": bool(r.report_object_key),
            "report_meta": r.report_meta,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    run = await _owned_run(db, user, run_id)
    project = await db.get(Project, run.project_id)
    return {
        "id": run.id,
        "project_id": run.project_id,
        "project_name": project.name,
        "template_key": project.template_key,
        "status": run.status,
        "current_round": run.current_round,
        "tokens_used": run.tokens_used,
        "error": run.error,
        "report_object_key": run.report_object_key,
        "report_meta": run.report_meta,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


async def _insights_payload(db: AsyncSession, run: Run, project: Project) -> dict:
    events = (
        await db.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run.id, RunEvent.event_type != "system")
            .order_by(RunEvent.round, RunEvent.seq_in_round)
        )
    ).all()
    agents = (await db.scalars(select(Agent).where(Agent.project_id == project.id))).all()
    names = {agent.id: agent.name for agent in agents}
    data = build_run_insights(events, names, project.language or "tr", run.current_round)
    return {
        "run": {
            "id": run.id,
            "project_id": project.id,
            "project_name": project.name,
            "template_key": project.template_key,
            "language": project.language,
            "status": run.status,
            "current_round": run.current_round,
            "report_ready": bool(run.report_object_key),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        },
        **data,
    }


@router.get("/runs/{run_id}/insights")
async def get_run_insights(
    run_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)
):
    run = await _owned_run(db, user, run_id)
    project = await db.get(Project, run.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="not found")
    return await _insights_payload(db, run, project)


@router.get("/runs/{run_id}/report")
async def get_run_report(
    run_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)
):
    run = await _owned_run(db, user, run_id)
    if not run.report_object_key:
        return {"ready": False, "meta": run.report_meta}
    meta = run.report_meta or {}
    return {
        "ready": True,
        "pdf_key": run.report_object_key,
        "md_key": meta.get("md_key"),
        "meta": meta,
    }


@router.get("/runs/{run_id}/report/download")
async def download_run_report(
    run_id: str,
    format: str = "pdf",
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
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


async def _owned_run(db: AsyncSession, user, run_id: str) -> Run:
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="not found")
    project = await db.get(Project, run.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    return run


@router.get("/runs/{run_id}/events")
async def list_run_events(
    run_id: str,
    after: int = 0,
    limit: int = 200,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await _owned_run(db, user, run_id)
    rows = (
        await db.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run.id, RunEvent.id > after)
            .order_by(RunEvent.id)
            .limit(min(max(limit, 1), 500))
        )
    ).all()
    return [
        {
            "id": ev.id,
            "round": ev.round,
            "platform": ev.platform,
            "event_type": ev.event_type,
            "agent_id": ev.agent_id,
            "payload": ev.payload,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in rows
    ]


@router.get("/runs/{run_id}/events/stream")
async def stream_run_events(
    run_id: str,
    request: Request,
    after: int = 0,
    user=Depends(current_user),
):
    async with AsyncSessionLocal() as s:
        await _owned_run(s, user, run_id)

    async def gen():
        last = after
        while True:
            if await request.is_disconnected():
                break
            async with AsyncSessionLocal() as s:
                current = await s.get(Run, run_id)
                events = (
                    await s.scalars(
                        select(RunEvent)
                        .where(RunEvent.run_id == run_id, RunEvent.id > last)
                        .order_by(RunEvent.id)
                        .limit(200)
                    )
                ).all()
                status = current.status if current else "failed"
                snapshot = {
                    "status": status,
                    "round": current.current_round if current else 0,
                    "tokens_used": current.tokens_used if current else 0,
                    "error": current.error if current else None,
                }
            yield f"event: status\ndata: {json.dumps(snapshot)}\n\n"
            for ev in events:
                last = ev.id
                payload = {
                    "id": ev.id,
                    "round": ev.round,
                    "platform": ev.platform,
                    "event_type": ev.event_type,
                    "agent_id": ev.agent_id,
                    "payload": ev.payload,
                }
                yield f"event: run_event\ndata: {json.dumps(payload)}\n\n"
            if status in TERMINAL_STATUSES and not events:
                break
            await asyncio.sleep(1)
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    run = await _owned_run(db, user, run_id)
    if run.status in ACTIVE_STATUSES:
        run.status = "canceled"
        run.finished_at = datetime.now(UTC)
        project = await db.get(Project, run.project_id)
        if project is not None:
            project.status = "canceled"
        await db.commit()
    return {"status": run.status}


@router.get("/projects/{project_id}/agents")
async def list_project_agents(
    project_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)
):
    project = (
        await db.scalars(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="not found")
    rows = (
        await db.scalars(
            select(Agent).where(Agent.project_id == project.id).order_by(Agent.agent_idx)
        )
    ).all()
    return [
        {
            "id": agent.id,
            "agent_idx": agent.agent_idx,
            "name": agent.name,
            "bio": agent.bio,
            "persona": agent.persona,
            "attributes": agent.attributes,
            "platform": agent.platform,
        }
        for agent in rows
    ]


@router.get("/projects/{project_id}/ontology")
async def get_project_ontology(
    project_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)
):
    project = (
        await db.scalars(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="not found")
    row = (
        await db.scalars(select(Ontology).where(Ontology.project_id == project.id))
    ).first()
    if row is None:
        return {"exists": False}
    return {
        "exists": True,
        "entity_types": row.entity_types,
        "relation_types": row.relation_types,
        "seed_summary": row.seed_summary,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
