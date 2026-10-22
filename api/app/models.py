"""SQLAlchemy models (mirrors db/init.sql)."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from app.config import settings


class Base(DeclarativeBase):
    pass


def uid() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uid()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    google_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_token_budget: Mapped[int] = mapped_column(BigInteger, default=1_000_000)
    monthly_token_used: Mapped[int] = mapped_column(BigInteger, default=0)
    billing_status: Mapped[str] = mapped_column(String(32), default="none")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    credit_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    billing_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingEvent(Base):
    __tablename__ = "billing_events"
    stripe_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlanConfig(Base):
    __tablename__ = "plan_configs"
    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    token_budget: Mapped[int] = mapped_column(BigInteger, default=1_000_000)
    agents: Mapped[int] = mapped_column(Integer, default=80)
    rounds: Mapped[int] = mapped_column(Integer, default=24)
    free_days: Mapped[int] = mapped_column(Integer, default=0)
    stripe_price_id: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditPack(Base):
    __tablename__ = "credit_packs"
    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    tokens: Mapped[int] = mapped_column(BigInteger)
    price_cents: Mapped[int] = mapped_column(Integer)
    stripe_price_id: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    delta: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String(64))
    stripe_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelConfig(Base):
    __tablename__ = "model_configs"
    task_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    model: Mapped[str] = mapped_column(String(128))
    fallbacks: Mapped[list[str]] = mapped_column(ARRAY(String(128)), default=list)
    max_tokens: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.7)
    top_p: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    rpm: Mapped[int] = mapped_column(Integer, default=60)
    tpm: Mapped[int] = mapped_column(BigInteger, default=200_000)
    daily_budget_tokens: Mapped[int] = mapped_column(BigInteger, default=3_000_000)
    monthly_budget_tokens: Mapped[int] = mapped_column(BigInteger, default=30_000_000)
    cost_in_usd_per_mtok: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    cost_out_usd_per_mtok: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Template(Base):
    __tablename__ = "templates"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    pack: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = uid()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(Text)
    template_key: Mapped[str] = mapped_column(String(64), default="market_research")
    language: Mapped[str] = mapped_column(String(8), default="tr")
    status: Mapped[str] = mapped_column(String(32), default="created")
    sim_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = uid()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text)
    minio_key: Mapped[str] = mapped_column(Text)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = uid()
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    chunk_idx: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(settings.embed_dim))

    __table_args__ = (Index("idx_chunks_tsv", "content"),)


class Ontology(Base):
    __tablename__ = "ontologies"
    id: Mapped[uuid.UUID] = uid()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True
    )
    entity_types: Mapped[dict] = mapped_column(JSONB)
    relation_types: Mapped[dict] = mapped_column(JSONB)
    seed_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[uuid.UUID] = uid()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    agent_idx: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(128))
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    platform: Mapped[str] = mapped_column(String(32), default="forum")
    memory: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = uid()
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    sim_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    token_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tokens_used: Mapped[int] = mapped_column(BigInteger, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    report_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunEvent(Base):
    __tablename__ = "run_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    round: Mapped[int] = mapped_column(Integer)
    platform: Mapped[str] = mapped_column(String(32), default="forum")
    seq_in_round: Mapped[int] = mapped_column(Integer)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BlogPost(Base):
    __tablename__ = "blog_posts"
    slug: Mapped[str] = mapped_column(String(120), primary_key=True)
    title_tr: Mapped[str] = mapped_column(Text)
    title_en: Mapped[str] = mapped_column(Text)
    excerpt_tr: Mapped[str] = mapped_column(Text, default="")
    excerpt_en: Mapped[str] = mapped_column(Text, default="")
    body_tr: Mapped[str] = mapped_column(Text, default="")
    body_en: Mapped[str] = mapped_column(Text, default="")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # --- SEO ---
    meta_description_tr: Mapped[str] = mapped_column(Text, default="")
    meta_description_en: Mapped[str] = mapped_column(Text, default="")
    focus_keyword_tr: Mapped[str] = mapped_column(String(160), default="")
    focus_keyword_en: Mapped[str] = mapped_column(String(160), default="")
    og_image: Mapped[str] = mapped_column(String(512), default="")
    canonical_url: Mapped[str] = mapped_column(String(512), default="")
    noindex: Mapped[bool] = mapped_column(Boolean, default=False)


class SeoSettings(Base):
    """Singleton row (id=1) with site-wide SEO / marketing configuration."""

    __tablename__ = "seo_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # site identity
    site_name: Mapped[str] = mapped_column(String(160), default="Social Simulator")
    site_url: Mapped[str] = mapped_column(String(256), default="")
    title_suffix: Mapped[str] = mapped_column(String(80), default="")
    default_description_tr: Mapped[str] = mapped_column(Text, default="")
    default_description_en: Mapped[str] = mapped_column(Text, default="")
    og_image: Mapped[str] = mapped_column(String(512), default="")
    twitter_site: Mapped[str] = mapped_column(String(80), default="")

    # crawling
    robots_extra: Mapped[str] = mapped_column(Text, default="")
    block_ai_bots: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_ai_bots: Mapped[str] = mapped_column(
        Text, default="GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot"
    )
    llms_txt: Mapped[str] = mapped_column(Text, default="")

    # verification
    google_site_verification: Mapped[str] = mapped_column(String(256), default="")
    bing_site_verification: Mapped[str] = mapped_column(String(256), default="")

    # indexnow
    indexnow_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    indexnow_key: Mapped[str] = mapped_column(String(128), default="")
    indexnow_endpoint: Mapped[str] = mapped_column(
        String(256), default="https://api.indexnow.org/indexnow"
    )

    # analytics
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    analytics_provider: Mapped[str] = mapped_column(String(32), default="ga4")
    analytics_id: Mapped[str] = mapped_column(String(128), default="")
    analytics_domain: Mapped[str] = mapped_column(String(160), default="")
    analytics_code: Mapped[str] = mapped_column(Text, default="")

    # ads
    ads_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    adsense_client: Mapped[str] = mapped_column(String(64), default="")
    adsense_slot: Mapped[str] = mapped_column(String(64), default="")
    adsense_slot_secondary: Mapped[str] = mapped_column(String(64), default="")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SeoPage(Base):
    """Per-route SEO overrides for static/marketing pages."""

    __tablename__ = "seo_pages"
    path: Mapped[str] = mapped_column(String(256), primary_key=True)
    title_tr: Mapped[str] = mapped_column(Text, default="")
    title_en: Mapped[str] = mapped_column(Text, default="")
    description_tr: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    og_image: Mapped[str] = mapped_column(String(512), default="")
    canonical_url: Mapped[str] = mapped_column(String(512), default="")
    focus_keyword: Mapped[str] = mapped_column(String(160), default="")
    noindex: Mapped[bool] = mapped_column(Boolean, default=False)
    sitemap_priority: Mapped[float] = mapped_column(Numeric(3, 2), default=0.7)
    changefreq: Mapped[str] = mapped_column(String(16), default="weekly")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SeoSubmission(Base):
    """IndexNow submission log (audit trail for admin)."""

    __tablename__ = "seo_submissions"
    id: Mapped[uuid.UUID] = uid()
    url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BlogTopic(Base):
    __tablename__ = "blog_topics"
    id: Mapped[uuid.UUID] = uid()
    topic: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="queued")
    post_slug: Mapped[str | None] = mapped_column(
        ForeignKey("blog_posts.slug", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BlogAutomation(Base):
    __tablename__ = "blog_automation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=7)
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = uid()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), default="default")
    prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Webhook(Base):
    __tablename__ = "webhooks"
    id: Mapped[uuid.UUID] = uid()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    secret: Mapped[str] = mapped_column(String(64))
    events: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TokenUsage(Base):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    task_key: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"
    id: Mapped[uuid.UUID] = uid()
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BreachLog(Base):
    __tablename__ = "security_breach_log"
    id: Mapped[uuid.UUID] = uid()
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str] = mapped_column(Text)
    affected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notified_residents: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_ag: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
