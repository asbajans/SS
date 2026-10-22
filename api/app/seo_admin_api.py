"""Admin endpoints for SEO / marketing: settings, page meta, audit, IndexNow."""
from __future__ import annotations

import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import admin_only
from app.auth import get_db
from app.config import settings
from app.models import BlogPost, SeoPage, SeoSettings, SeoSubmission
from app.seo import (
    STATIC_PAGES,
    SimilarityIndex,
    abs_url,
    keyword_density,
    normalize_base_url,
    strip_markup,
)

router = APIRouter(prefix="/api/admin/seo", tags=["admin-seo"])

MIN_DESC = 70
MAX_DESC = 165
MIN_BODY_WORDS = 250


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


class SettingsIn(BaseModel):
    site_name: str = Field(default="Social Simulator", max_length=160)
    site_url: str = Field(default="", max_length=256)
    title_suffix: str = Field(default="", max_length=80)
    default_description_tr: str = Field(default="", max_length=500)
    default_description_en: str = Field(default="", max_length=500)
    og_image: str = Field(default="", max_length=512)
    twitter_site: str = Field(default="", max_length=80)

    robots_extra: str = Field(default="", max_length=4000)
    block_ai_bots: bool = False
    allow_ai_bots: str = Field(default="", max_length=1000)
    llms_txt: str = Field(default="", max_length=8000)

    google_site_verification: str = Field(default="", max_length=256)
    bing_site_verification: str = Field(default="", max_length=256)

    indexnow_enabled: bool = False
    indexnow_key: str = Field(default="", max_length=128)
    indexnow_endpoint: str = Field(default="https://api.indexnow.org/indexnow", max_length=256)

    analytics_enabled: bool = False
    analytics_provider: str = Field(default="ga4", max_length=32)
    analytics_id: str = Field(default="", max_length=128)
    analytics_domain: str = Field(default="", max_length=160)

    ads_enabled: bool = False
    adsense_client: str = Field(default="", max_length=64)
    adsense_slot: str = Field(default="", max_length=64)
    adsense_slot_secondary: str = Field(default="", max_length=64)


class PageIn(BaseModel):
    title_tr: str = Field(default="", max_length=300)
    title_en: str = Field(default="", max_length=300)
    description_tr: str = Field(default="", max_length=500)
    description_en: str = Field(default="", max_length=500)
    og_image: str = Field(default="", max_length=512)
    canonical_url: str = Field(default="", max_length=512)
    focus_keyword: str = Field(default="", max_length=160)
    noindex: bool = False
    sitemap_priority: float = Field(default=0.7, ge=0.0, le=1.0)
    changefreq: str = Field(default="weekly", max_length=16)


class PostSeoIn(BaseModel):
    meta_description_tr: str = Field(default="", max_length=500)
    meta_description_en: str = Field(default="", max_length=500)
    focus_keyword_tr: str = Field(default="", max_length=160)
    focus_keyword_en: str = Field(default="", max_length=160)
    og_image: str = Field(default="", max_length=512)
    canonical_url: str = Field(default="", max_length=512)
    noindex: bool = False


class SubmitIn(BaseModel):
    urls: list[str] = Field(default_factory=list, max_length=200)
    all_pages: bool = False


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


async def _row(db: AsyncSession) -> SeoSettings:
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


def _settings_payload(row: SeoSettings) -> dict:
    return {
        "site_name": row.site_name,
        "site_url": row.site_url,
        "effective_site_url": normalize_base_url(row.site_url or settings.public_base_url),
        "title_suffix": row.title_suffix,
        "default_description_tr": row.default_description_tr,
        "default_description_en": row.default_description_en,
        "og_image": row.og_image,
        "twitter_site": row.twitter_site,
        "robots_extra": row.robots_extra,
        "block_ai_bots": row.block_ai_bots,
        "allow_ai_bots": row.allow_ai_bots,
        "llms_txt": row.llms_txt,
        "google_site_verification": row.google_site_verification,
        "bing_site_verification": row.bing_site_verification,
        "indexnow_enabled": row.indexnow_enabled,
        "indexnow_key": row.indexnow_key,
        "indexnow_endpoint": row.indexnow_endpoint,
        "analytics_enabled": row.analytics_enabled,
        "analytics_provider": row.analytics_provider,
        "analytics_id": row.analytics_id,
        "analytics_domain": row.analytics_domain,
        "ads_enabled": row.ads_enabled,
        "adsense_client": row.adsense_client,
        "adsense_slot": row.adsense_slot,
        "adsense_slot_secondary": row.adsense_slot_secondary,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _page_payload(p: SeoPage) -> dict:
    return {
        "path": p.path,
        "title_tr": p.title_tr,
        "title_en": p.title_en,
        "description_tr": p.description_tr,
        "description_en": p.description_en,
        "og_image": p.og_image,
        "canonical_url": p.canonical_url,
        "focus_keyword": p.focus_keyword,
        "noindex": p.noindex,
        "sitemap_priority": float(p.sitemap_priority),
        "changefreq": p.changefreq,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _post_payload(p: BlogPost) -> dict:
    return {
        "slug": p.slug,
        "title_tr": p.title_tr,
        "title_en": p.title_en,
        "is_published": p.is_published,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "meta_description_tr": p.meta_description_tr,
        "meta_description_en": p.meta_description_en,
        "focus_keyword_tr": p.focus_keyword_tr,
        "focus_keyword_en": p.focus_keyword_en,
        "og_image": p.og_image,
        "canonical_url": p.canonical_url,
        "noindex": p.noindex,
    }


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------


@router.get("", dependencies=[Depends(admin_only)])
async def get_settings(db: AsyncSession = Depends(get_db)) -> dict:
    row = await _row(db)
    pages = (await db.scalars(select(SeoPage).order_by(SeoPage.path))).all()
    posts = (await db.scalars(select(BlogPost).order_by(BlogPost.published_at.desc()))).all()
    return {
        "settings": _settings_payload(row),
        "pages": [_page_payload(p) for p in pages],
        "static_pages": STATIC_PAGES,
        "posts": [_post_payload(p) for p in posts],
    }


@router.put("", dependencies=[Depends(admin_only)])
async def put_settings(payload: SettingsIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _row(db)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return _settings_payload(row)


@router.post("/indexnow/key", dependencies=[Depends(admin_only)])
async def regenerate_indexnow_key(db: AsyncSession = Depends(get_db)) -> dict:
    row = await _row(db)
    row.indexnow_key = secrets.token_hex(16)
    await db.commit()
    await db.refresh(row)
    return {"indexnow_key": row.indexnow_key}


# --------------------------------------------------------------------------
# Per-page meta
# --------------------------------------------------------------------------


@router.put("/pages/{path:path}", dependencies=[Depends(admin_only)])
async def upsert_page(path: str, payload: PageIn, db: AsyncSession = Depends(get_db)) -> dict:
    key = "/" + path.strip("/")
    row = await db.get(SeoPage, key)
    if row is None:
        row = SeoPage(path=key)
        db.add(row)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return _page_payload(row)


@router.delete("/pages/{path:path}", dependencies=[Depends(admin_only)])
async def delete_page(path: str, db: AsyncSession = Depends(get_db)) -> dict:
    key = "/" + path.strip("/")
    row = await db.get(SeoPage, key)
    if row is None:
        raise HTTPException(status_code=404, detail="page meta not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.patch("/posts/{slug}", dependencies=[Depends(admin_only)])
async def update_post_seo(slug: str, payload: PostSeoIn, db: AsyncSession = Depends(get_db)) -> dict:
    post = await db.get(BlogPost, slug)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    for field, value in payload.model_dump().items():
        setattr(post, field, value)
    await db.commit()
    await db.refresh(post)
    return _post_payload(post)


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------


@router.get("/audit", dependencies=[Depends(admin_only)])
async def audit(db: AsyncSession = Depends(get_db)) -> dict:
    """Content + technical SEO audit for the whole public surface."""
    row = await _row(db)
    base = normalize_base_url(row.site_url or settings.public_base_url)
    posts = list(
        (
            await db.scalars(
                select(BlogPost).where(BlogPost.is_published.is_(True)).order_by(BlogPost.published_at.desc())
            )
        ).all()
    )
    pages = {p.path: p for p in (await db.scalars(select(SeoPage))).all()}

    issues: list[dict] = []
    warnings: list[dict] = []

    def add(level: str, scope: str, ref: str, message: str, fix: str = "") -> None:
        (issues if level == "error" else warnings).append(
            {"level": level, "scope": scope, "ref": ref, "message": message, "fix": fix}
        )

    # --- site level ---
    if not row.site_url:
        add("error", "site", "-", "Site URL tanımlı değil; sitemap ve IndexNow mutlak adres üretemez.",
            "SEO ayarlarından site URL girin.")
    if not row.default_description_tr:
        add("warning", "site", "/", "Varsayılan meta açıklama (TR) boş.", "Ana sayfa açıklamasını yazın.")
    if not row.default_description_en:
        add("warning", "site", "/", "Varsayılan meta açıklama (EN) boş.", "İngilizce açıklamayı yazın.")
    if not row.og_image:
        add(
            "warning",
            "site",
            "-",
            "OG görseli yok; paylaşımlarda görsel çıkmaz.",
            "1200x630 bir OG görseli tanımlayın.",
        )


    # --- static pages ---
    for page in STATIC_PAGES:
        ov = pages.get(page["path"])
        if ov is None:
            add("info", "page", page["path"], "Sayfa meta override'ı yok (varsayılanlar kullanılıyor).")
            continue
        desc = ov.description_tr or row.default_description_tr
        if not desc:
            add("warning", "page", page["path"], "Meta açıklama yok.")
        elif len(desc) < MIN_DESC:
            add(
                "warning",
                "page",
                page["path"],
                f"Meta açıklama kısa ({len(desc)} karakter, önerilen {MIN_DESC}-{MAX_DESC}).",
            )
        elif len(desc) > MAX_DESC:
            add(
                "warning",
                "page",
                page["path"],
                f"Meta açıklama uzun ({len(desc)} karakter), arama sonucunda kırpılır.",
            )

    # --- blog posts ---
    index = SimilarityIndex()
    for post in posts:
        body_tr = strip_markup(post.body_tr)
        words = len(body_tr.split())
        desc = post.meta_description_tr or post.excerpt_tr
        key = f"/blog/{post.slug}"
        index.add(key, body_tr, post.title_tr)
        if not post.meta_description_tr:
            add("warning", "post", key, "Kendi meta açıklaması yok; özet metni kullanılıyor.")
        elif len(post.meta_description_tr) < MIN_DESC:
            add("warning", "post", key, f"Meta açıklama kısa ({len(post.meta_description_tr)} karakter).")
        elif len(post.meta_description_tr) > MAX_DESC:
            add("warning", "post", key, f"Meta açıklama uzun ({len(post.meta_description_tr)} karakter).")
        if not post.focus_keyword_tr:
            add("info", "post", key, "Odak anahtar kelime tanımlı değil.")
        if words < MIN_BODY_WORDS:
            add("warning", "post", key, f"İnce içerik ({words} kelime); zenginleştirin.")
        if not post.og_image:
            add("info", "post", key, "Kendi OG görseli yok.")
        if post.noindex:
            add("info", "post", key, "noindex işaretli; sitemap'e girmez.")
        if not post.body_en.strip() and post.title_en.strip():
            add(
                "warning",
                "post",
                key,
                "İngilizce gövde boş.",
                "EN içeriği ekleyin veya EN başlığını temizleyin.",
            )

        elif post.body_en.strip():
            en_words = len(strip_markup(post.body_en).split())
            if en_words < MIN_BODY_WORDS:
                add("warning", "post", key, f"İngilizce içerik ince ({en_words} kelime).")

    # --- duplicate content ---
    for pair in index.pairs(threshold=0.30):
        add(
            "error",
            "duplicate",
            f"{pair.left} ↔ {pair.right}",
            f"Neredeyse aynı içerik (%{round(pair.similarity * 100)} benzerlik, {pair.kind}).",
            "Metni yeniden yazın veya birini kaldırın.",
        )

    # --- keyword density ---
    density: list[dict] = []
    for post in posts:
        if not post.focus_keyword_tr:
            continue
        body = strip_markup(post.body_tr)
        d = keyword_density(body, post.focus_keyword_tr)
        density.append(
            {
                "slug": post.slug,
                "keyword": post.focus_keyword_tr,
                "density": d,
                "words": len(body.split()),
            }
        )

        if d == 0:
            add("warning", "post", f"/blog/{post.slug}",
                f"Odak kelime (“{post.focus_keyword_tr}”) gövdede geçmiyor.")
        elif d > 3.5:
            add("warning", "post", f"/blog/{post.slug}",
                f"Odak kelime yoğunluğu çok yüksek (%{d}); anahtar kelime yığılması riski.")

    # --- indexnow readiness ---
    if row.indexnow_enabled:
        if not row.indexnow_key:
            add("error", "indexnow", "-", "IndexNow açık ama anahtar boş.", "Anahtar üretin.")
        elif len(row.indexnow_key) < 8:
            add("warning", "indexnow", "-", "IndexNow anahtarı çok kısa.")

    score = 100
    score -= min(40, len(issues) * 10)
    score -= min(40, len(warnings) * 3)
    score = max(0, score)

    return {
        "score": score,
        "error_count": len(issues),
        "warning_count": len(warnings),
        "issues": issues,
        "warnings": warnings,
        "duplicate_pairs": [p.as_dict() for p in index.pairs(threshold=0.30)],
        "keyword_density": density,
        "stats": {
            "posts": len(posts),
            "pages": len(STATIC_PAGES),
            "words": sum(len(strip_markup(p.body_tr).split()) for p in posts),
        },
        "site_url": base,
    }


# --------------------------------------------------------------------------
# IndexNow
# --------------------------------------------------------------------------


@router.get("/indexnow/log", dependencies=[Depends(admin_only)])
async def indexnow_log(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.scalars(select(SeoSubmission).order_by(SeoSubmission.created_at.desc()).limit(100))
    ).all()
    return [
        {
            "id": str(r.id),
            "url": r.url,
            "status": r.status,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/indexnow/submit", dependencies=[Depends(admin_only)])
async def submit_indexnow(payload: SubmitIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _row(db)
    if not row.indexnow_enabled:
        raise HTTPException(status_code=400, detail="IndexNow kapalı")
    if not row.indexnow_key:
        raise HTTPException(status_code=400, detail="IndexNow anahtarı tanımlı değil")

    base = normalize_base_url(row.site_url or settings.public_base_url)
    urls: list[str] = []
    if payload.all_pages:
        urls.append(abs_url(base, "/"))
        urls.append(abs_url(base, "/blog"))
        posts = (
            await db.scalars(select(BlogPost).where(BlogPost.is_published.is_(True)))
        ).all()
        urls.extend(abs_url(base, f"/blog/{p.slug}") for p in posts)
    else:
        for raw in payload.urls:
            url = raw.strip()
            if not url:
                continue
            if not url.startswith(("http://", "https://")):
                url = abs_url(base, url)
            urls.append(url)

    urls = list(dict.fromkeys(urls))
    if not urls:
        raise HTTPException(status_code=400, detail="gönderilecek URL yok")

    body = {
        "host": base.split("://", 1)[-1].split("/")[0],
        "key": row.indexnow_key,
        "keyLocation": f"{base}/{row.indexnow_key}.txt",
        "urlList": urls,
    }
    endpoint = row.indexnow_endpoint or "https://api.indexnow.org/indexnow"
    status = "failed"
    detail = ""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(endpoint, json=body, headers={"Content-Type": "application/json"})
        status = "ok" if resp.status_code in (200, 202) else "failed"
        detail = f"HTTP {resp.status_code} {resp.text[:300]}"
    except Exception as exc:  # noqa: BLE001
        detail = str(exc)[:300]

    db.add(
        SeoSubmission(
            url=",".join(urls[:5]) + (f" (+{len(urls) - 5} more)" if len(urls) > 5 else ""),
            status=status,
            detail=detail,
        )
    )
    await db.commit()
    return {"ok": status == "ok", "status": status, "detail": detail, "submitted": len(urls), "urls": urls}
