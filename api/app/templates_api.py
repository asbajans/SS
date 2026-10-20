"""Topic template catalog + admin CRUD."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import admin_only
from app.auth import current_user, get_db
from app.models import Project, Template
from engine.templates import validate_pack

router = APIRouter(prefix="/api", tags=["templates"])

KEY_RE = re.compile(r"^[a-z0-9_]{2,64}$")


class TemplateIn(BaseModel):
    name: str
    description: str = ""
    pack: dict
    is_active: bool = True


def _public_row(t: Template) -> dict:
    pack = t.pack or {}
    return {
        "key": t.key,
        "name": t.name,
        "description": t.description,
        "is_active": t.is_active,
        "is_builtin": t.is_builtin,
        "sim_defaults": pack.get("sim_defaults") or {},
        "action_space": pack.get("action_space") or [],
    }


def _full_row(t: Template) -> dict:
    row = _public_row(t)
    row["pack"] = t.pack or {}
    return row


@router.get("/templates", dependencies=[Depends(current_user)])
async def list_templates(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.scalars(
            select(Template).where(Template.is_active.is_(True)).order_by(Template.name)
        )
    ).all()
    return [_public_row(t) for t in rows]


@router.get("/admin/templates", dependencies=[Depends(admin_only)])
async def admin_list_templates(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Template).order_by(Template.name))).all()
    return [_full_row(t) for t in rows]


@router.put("/admin/templates/{key}", dependencies=[Depends(admin_only)])
async def upsert_template(key: str, data: TemplateIn, db: AsyncSession = Depends(get_db)):
    if not KEY_RE.match(key):
        raise HTTPException(
            status_code=400, detail="anahtar 2-64 karakter, küçük harf/rakam/alt çizgi olmalı"
        )
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="şablon adı zorunlu")
    err = validate_pack(data.pack)
    if err:
        raise HTTPException(status_code=400, detail=err)
    row = await db.get(Template, key)
    if row is None:
        row = Template(key=key, is_builtin=False)
    row.name = data.name.strip()[:160]
    row.description = data.description.strip()[:1000]
    row.pack = data.pack
    row.is_active = data.is_active
    db.add(row)
    await db.commit()
    return _full_row(row)


@router.delete("/admin/templates/{key}", dependencies=[Depends(admin_only)])
async def delete_template(key: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Template, key)
    if row is None:
        raise HTTPException(status_code=404, detail="şablon bulunamadı")
    if row.is_builtin:
        raise HTTPException(
            status_code=400, detail="yerleşik şablon silinemez; pasife alabilirsiniz"
        )
    used = await db.scalar(
        select(func.count()).select_from(Project).where(Project.template_key == key)
    )
    if used:
        raise HTTPException(status_code=400, detail=f"{used} proje bu şablonu kullanıyor")
    await db.delete(row)
    await db.commit()
    return {"deleted": True}
