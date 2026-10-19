"""FastAPI app factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.admin_api import router as admin_router
from app.auth import router as auth_router
from app.billing_api import router as billing_router
from app.health import router as health_router
from app.runs_api import router as runs_router
from app.startup import create_first_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_first_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="CrowdScope API", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(runs_router)
    app.include_router(admin_router)
    app.include_router(billing_router)
    return app


app = create_app()
