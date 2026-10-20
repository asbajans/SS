"""FastAPI app factory."""
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from app.admin_api import router as admin_router
from app.auth import router as auth_router
from app.billing_api import router as billing_router
from app.config import settings
from app.documents_api import router as documents_router
from app.health import router as health_router
from app.llm_gateway.router import router as llm_router
from app.privacy_api import router as privacy_router
from app.runs_api import router as runs_router
from app.startup import create_first_admin, ensure_schema, seed_templates
from app.templates_api import router as templates_router


def _metrics_app() -> Starlette:
    async def metrics(request):
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return Starlette(routes=[Route("/metrics", metrics)])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_schema()
    await seed_templates()
    await create_first_admin()
    server = None
    task = None
    if settings.metrics_port:
        config = uvicorn.Config(
            _metrics_app(),
            host="0.0.0.0",  # noqa: S104
            port=settings.metrics_port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())
    yield
    if server is not None and task is not None:
        server.should_exit = True
        await task


def create_app() -> FastAPI:
    app = FastAPI(title="Social Simulation API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(runs_router)
    app.include_router(admin_router)
    app.include_router(billing_router)
    app.include_router(llm_router)
    app.include_router(documents_router)
    app.include_router(templates_router)
    app.include_router(privacy_router)
    Instrumentator(excluded_handlers=["/metrics"]).instrument(app)
    return app


app = create_app()
