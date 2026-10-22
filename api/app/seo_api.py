"""Public SEO / marketing endpoints: sitemap, robots, llms.txt, RSS, runtime config.

These are consumed by crawlers, feed readers and the SPA at runtime, so they
must stay public (no auth) and cheap to cache.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_db
from app.config import settings
from app.models import BlogPost, SeoPage, SeoSettings
from app.seo import (
    STATIC_PAGES,
    abs_url,
    article_jsonld,
    iso,
    llms_txt,
    normalize_base_url,
    organization_jsonld,
    rfc822,
    robots_txt,
    rss_xml,
    sitemap_index_xml,
    urlset_xml,
    website_jsonld,
)

router = APIRouter(tags=["seo"])

XML = "application/xml; charset=utf-8"
TEXT = "text/plain; charset=utf-8"


async def _settings_row(db: AsyncSession) -> SeoSettings:
    row = await db.get(SeoSettings, 1)
    if row is None:
        row = SeoSettings(
            id=1,
            site_url=settings.public_base_url,
            indexnow_enabled=settings.indexnow_enabled,
            indexnow_key=settings.indexnow_key,
            indexnow_endpoint=settings.indexnow_endpoint or "https://api.indexnow.org/indexnow",
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def _base_url(row: SeoSettings) -> str:
    return normalize_base_url(row.site_url or settings.public_base_url)


async def _published_posts(db: AsyncSession) -> list[BlogPost]:
    return list(
        (
            await db.scalars(
                select(BlogPost)
                .where(BlogPost.is_published.is_(True))
                .order_by(BlogPost.published_at.desc())
            )
        ).all()
    )


# --------------------------------------------------------------------------
# Sitemaps
# --------------------------------------------------------------------------


@router.get("/sitemap.xml")
async def sitemap_index(db: AsyncSession = Depends(get_db)) -> Response:
    row = await _settings_row(db)
    base = _base_url(row)
    lastmod = iso(row.updated_at) or iso(None)
    body = sitemap_index_xml(
        base,
        [
            {"path": "sitemap-pages.xml", "lastmod": lastmod},
            {"path": "sitemap-blog.xml", "lastmod": lastmod},
        ],
    )
    return Response(content=body, media_type=XML, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap-pages.xml")
async def sitemap_pages(db: AsyncSession = Depends(get_db)) -> Response:
    row = await _settings_row(db)
    base = _base_url(row)
    overrides = {
        p.path: p
        for p in (await db.scalars(select(SeoPage))).all()
    }
    entries: list[dict] = []
    for page in STATIC_PAGES:
        ov = overrides.get(page["path"])
        if ov is not None and ov.noindex:
            continue
        entries.append(
            {
                "url": abs_url(base, page["path"]),
                "lastmod": iso(ov.updated_at) if ov else None,
                "changefreq": ov.changefreq if ov else page["changefreq"],
                "priority": float(ov.sitemap_priority) if ov else page["priority"],
                "images": [abs_url(base, ov.og_image)] if ov and ov.og_image else [],
            }
        )
    body = urlset_xml(entries)
    return Response(content=body, media_type=XML, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap-blog.xml")
async def sitemap_blog(db: AsyncSession = Depends(get_db)) -> Response:
    row = await _settings_row(db)
    base = _base_url(row)
    posts = await _published_posts(db)
    entries = []
    for post in posts:
        if post.noindex:
            continue
        entries.append(
            {
                "url": abs_url(base, f"/blog/{post.slug}"),
                "lastmod": iso(post.updated_at),
                "changefreq": "monthly",
                "priority": 0.8,
                "images": [abs_url(base, post.og_image)] if post.og_image else [],
            }
        )
    body = urlset_xml(entries)
    return Response(content=body, media_type=XML, headers={"Cache-Control": "public, max-age=3600"})


# --------------------------------------------------------------------------
# robots.txt / llms.txt / RSS
# --------------------------------------------------------------------------


@router.get("/robots.txt")
async def robots(db: AsyncSession = Depends(get_db)) -> Response:
    row = await _settings_row(db)
    body = robots_txt(
        _base_url(row),
        block_ai_bots=row.block_ai_bots,
        allow_ai_bots=row.allow_ai_bots,
        extra=row.robots_extra,
    )
    return Response(content=body, media_type=TEXT, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/llms.txt")
async def llms(db: AsyncSession = Depends(get_db)) -> Response:
    """llmstxt.org style index so LLM crawlers can navigate the site cheaply."""
    row = await _settings_row(db)
    base = _base_url(row)
    posts = await _published_posts(db)
    sections: list[dict] = [
        {
            "title": row.site_name or "Social Simulator",
            "description": row.default_description_tr
            or "Sentetik topluluk simülasyonu platformu.",
            "items": [
                {
                    "title": "Ana sayfa",
                    "url": abs_url(base, "/"),
                    "note": "Ürün tanıtımı, özellikler ve fiyatlandırma.",
                },
                {
                    "title": "Blog",
                    "url": abs_url(base, "/blog"),
                    "note": "Sektörel analizler ve metodoloji yazıları.",
                },
            ],
        }
    ]
    if posts:
        sections.append(
            {
                "title": "Blog yazıları",
                "description": "Yayımlanmış tüm yazılar.",
                "items": [
                    {
                        "title": p.title_tr,
                        "url": abs_url(base, f"/blog/{p.slug}"),
                        "note": (p.excerpt_tr or p.meta_description_tr or "")[:180],
                    }
                    for p in posts
                ],
            }
        )
    if row.llms_txt.strip():
        sections.append({"title": "Ek notlar", "description": row.llms_txt.strip(), "items": []})
    body = llms_txt(base, sections)
    return Response(content=body, media_type=TEXT, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/llms-full.txt")
async def llms_full(db: AsyncSession = Depends(get_db)) -> Response:
    """Full plain-text corpus — the machine readable version of the whole site."""
    row = await _settings_row(db)
    base = _base_url(row)
    posts = await _published_posts(db)
    lines = [f"# {row.site_name or 'Social Simulator'} — tam içerik", ""]
    lines.append(f"Base URL: {base}/")
    lines.append(f"Last updated: {iso(row.updated_at)}")
    lines.append("")
    lines.append("## Ana sayfa")
    lines.append("")
    lines.append(row.default_description_tr or "")
    lines.append("")
    for post in posts:
        lines.append(f"## {post.title_tr}")
        lines.append("")
        lines.append(f"URL: {abs_url(base, f'/blog/{post.slug}')}")
        if post.excerpt_tr:
            lines.append(f"Summary: {post.excerpt_tr}")
        lines.append("")
        lines.append(post.body_tr)
        lines.append("")
    body = "\n".join(lines)
    return Response(content=body, media_type=TEXT, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/feed.xml")
async def rss_feed(db: AsyncSession = Depends(get_db)) -> Response:
    row = await _settings_row(db)
    base = _base_url(row)
    posts = await _published_posts(db)
    items = [
        {
            "title": p.title_tr,
            "url": abs_url(base, f"/blog/{p.slug}"),
            "description": p.excerpt_tr or p.meta_description_tr or "",
            "pubdate": rfc822(p.published_at),
        }
        for p in posts
    ]
    body = rss_xml(base, row.site_name or "Social Simulator", items, row.default_description_tr)
    return Response(content=body, media_type=XML, headers={"Cache-Control": "public, max-age=1800"})


@router.get("/indexnow-key.txt")
async def indexnow_key_file(db: AsyncSession = Depends(get_db)) -> Response:
    """IndexNow key verification file (also served at /{key}.txt by nginx)."""
    row = await _settings_row(db)
    if not row.indexnow_key:
        raise HTTPException(status_code=404, detail="indexnow key not configured")
    headers = {"Cache-Control": "public, max-age=86400"}
    return Response(content=row.indexnow_key, media_type=TEXT, headers=headers)


@router.get("/{key}.txt")
async def indexnow_key_dynamic(key: str, db: AsyncSession = Depends(get_db)) -> Response:
    """IndexNow requires the key to be hosted at the domain root as {key}.txt."""
    row = await _settings_row(db)
    if not row.indexnow_key or key != row.indexnow_key:
        raise HTTPException(status_code=404, detail="not found")
    headers = {"Cache-Control": "public, max-age=86400"}
    return Response(content=row.indexnow_key, media_type=TEXT, headers=headers)


# --------------------------------------------------------------------------
# Runtime config consumed by the SPA (analytics / ads injection)
# --------------------------------------------------------------------------


@router.get("/api/seo/runtime")
async def seo_runtime(db: AsyncSession = Depends(get_db)) -> dict:
    row = await _settings_row(db)
    return {
        "site_name": row.site_name,
        "site_url": _base_url(row),
        "title_suffix": row.title_suffix,
        "default_description_tr": row.default_description_tr,
        "default_description_en": row.default_description_en,
        "og_image": row.og_image,
        "twitter_site": row.twitter_site,
        "google_site_verification": row.google_site_verification,
        "bing_site_verification": row.bing_site_verification,
        "analytics": {
            "enabled": row.analytics_enabled,
            "provider": row.analytics_provider,
            "id": row.analytics_id,
            "domain": row.analytics_domain,
        },
        "ads": {
            "enabled": row.ads_enabled,
            "client": row.adsense_client,
            "slot": row.adsense_slot,
            "slot_secondary": row.adsense_slot_secondary,
        },
    }


@router.get("/api/seo/pages")
async def seo_pages(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Public per-page meta so the SPA can render titles/descriptions."""
    rows = (await db.scalars(select(SeoPage).order_by(SeoPage.path))).all()
    return [
        {
            "path": p.path,
            "title_tr": p.title_tr,
            "title_en": p.title_en,
            "description_tr": p.description_tr,
            "description_en": p.description_en,
            "og_image": p.og_image,
            "canonical_url": p.canonical_url,
            "noindex": p.noindex,
        }
        for p in rows
    ]


@router.get("/api/seo/jsonld/{slug}")
async def seo_jsonld(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    """JSON-LD graph for a blog post (schema.org BlogPosting + Organization)."""
    row = await _settings_row(db)
    base = _base_url(row)
    post = await db.get(BlogPost, slug)
    if post is None or not post.is_published:
        raise HTTPException(status_code=404, detail="post not found")
    return {
        "@context": "https://schema.org",
        "@graph": [
            organization_jsonld(base, row.site_name, row.og_image),
            website_jsonld(base, row.site_name, row.default_description_tr),
            article_jsonld(
                base_url=base,
                title=post.title_tr,
                description=post.meta_description_tr or post.excerpt_tr,
                path=f"/blog/{post.slug}",
                published_at=post.published_at,
                updated_at=post.updated_at,
                author=row.site_name,
                image=post.og_image or row.og_image,
                keywords=post.focus_keyword_tr,
            ),
        ]
    }
