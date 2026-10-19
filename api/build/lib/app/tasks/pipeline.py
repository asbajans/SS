"""Pipeline orchestration: ingest -> ontology -> population -> loop -> report."""
import asyncio
from datetime import UTC

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="pipeline.run", max_retries=0, soft_time_limit=3 * 3600 - 60)
def run_pipeline(run_id: str) -> dict:
    try:
        return asyncio.run(_run(run_id))
    except Exception as e:  # noqa: BLE001
        log.exception("pipeline_failed", run_id=run_id)
        asyncio.run(_set_status(run_id, "failed", error=str(e)))
        return {"status": "failed", "error": str(e)}


async def _set_status(run_id: str, status: str, **extra) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db import engine
    from app.models import Run

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        run = await session.get(Run, run_id)
        if run is None:
            return
        run.status = status
        for k, v in extra.items():
            setattr(run, k, v)
        if status == "running":
            from datetime import datetime

            run.started_at = datetime.now(UTC)
        await session.commit()


async def _run_pipeline(run_id: str) -> dict:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db import engine
    from app.models import Project, Run

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        await _set_status(session, run_id, "running")
        run = await session.get(Run, run_id)
        project = await session.get(Project, run.project_id)
        template_key = project.template_key

    # placeholder: full stages land in F2 (agent.md s8)
    log.info("pipeline_placeholder", run_id=run_id, template=template_key)
    await _set_status(session, run_id, "completed")
    return {"status": "completed"}


async def _run(run_id: str) -> dict:
    try:
        return await _run_pipeline(run_id)
    except Exception as e:  # noqa: BLE001
        await _set_status(run_id, "failed", error=str(e))
        return {"status": "failed", "error": str(e)}
