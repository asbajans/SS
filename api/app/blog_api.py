"""Public marketing blog."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_db
from app.models import BlogPost

router = APIRouter(prefix="/api/blog", tags=["blog"])


def _summary(post: BlogPost) -> dict:
    return {
        "slug": post.slug,
        "title_tr": post.title_tr,
        "title_en": post.title_en,
        "excerpt_tr": post.excerpt_tr,
        "excerpt_en": post.excerpt_en,
        "meta_description_tr": post.meta_description_tr,
        "meta_description_en": post.meta_description_en,
        "focus_keyword_tr": post.focus_keyword_tr,
        "focus_keyword_en": post.focus_keyword_en,
        "og_image": post.og_image,
        "canonical_url": post.canonical_url,
        "noindex": post.noindex,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


@router.get("/posts")
async def list_posts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(
            select(BlogPost)
            .where(BlogPost.is_published.is_(True))
            .order_by(BlogPost.published_at.desc())
        )
    ).all()
    return [_summary(p) for p in rows]


@router.get("/posts/{slug}")
async def get_post(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    post = await db.get(BlogPost, slug)
    if post is None or not post.is_published:
        raise HTTPException(status_code=404, detail="post not found")
    return {
        **_summary(post),
        "body_tr": post.body_tr,
        "body_en": post.body_en,
    }
