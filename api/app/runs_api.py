"""Runs router (thick logic lives in Celery pipeline; see agent.md s8)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, get_db
from app.models import Project, Run

router = APIRouter(prefix="/api")


def _validate_sim_config(cfg: dict) -> str | None:
    agents_n = cfg.get("agents_n")
    if not isinstance(agents_n, int) or not (1 <= agents_n <= 300):
        return "agents_n must be an integer between 1 and 300"
    rounds = cfg.get("rounds")
    if not isinstance(rounds, int) or not (1 <= rounds <= 120):
        return "rounds must be an integer between 1 and 120"
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


@router.post("/projects", status_code=201)
async def create_project(data: ProjectIn, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    invalid = _validate_sim_config(data.sim_config)
    if invalid:
        raise HTTPException(status_code=400, detail=invalid)
    template_key = data.template_key
    from engine.templates import get_template
    try:
        get_template(template_key)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
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
    names = {
        p.id: p.name
        for p in (await db.scalars(select(Project).where(Project.id.in_(ids)))).all()
    }
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "project_name": names.get(r.project_id),
            "status": r.status,
            "current_round": r.current_round,
            "tokens_used": r.tokens_used,
            "cost_usd": str(r.cost_usd),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="not found")
    project = await db.get(Project, run.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": run.id,
        "project_id": run.project_id,
        "project_name": project.name,
        "template_key": project.template_key,
        "status": run.status,
        "current_round": run.current_round,
        "tokens_used": run.tokens_used,
        "cost_usd": str(run.cost_usd),
        "error": run.error,
        "report_object_key": run.report_object_key,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
