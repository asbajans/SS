"""Health endpoints."""
from fastapi import APIRouter
from sqlalchemy import text

from app.db import AsyncSessionLocal

router = APIRouter(prefix="/health")


@router.get("")
async def healthz() -> dict:
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("select 1"))
        return {"ok": True, "db": "up"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "db": "down", "error": str(e)}
