"""Load topic templates from DB with builtin fallback."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Template
from engine.templates import TopicTemplate, get_template, template_from_pack


async def load_template(s: AsyncSession, key: str) -> TopicTemplate:
    row = await s.get(Template, key)
    if row is not None and row.is_active:
        return template_from_pack(row.key, row.name, row.pack or {}, row.description or "")
    return get_template(key)


async def active_template(s: AsyncSession, key: str) -> Template | None:
    row = await s.get(Template, key)
    if row is None or not row.is_active:
        return None
    return row
