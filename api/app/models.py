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
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from app.config import settings


class Base(DeclarativeBase):
    pass


def uid() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = uid()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    plan: Mapped[str] = mapped_column(String(32), default="free")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_token_budget: Mapped[int] = mapped_column(BigInteger, default=1_000_000)
    monthly_token_used: Mapped[int] = mapped_column(BigInteger, default=0)
    billing_status: Mapped[str] = mapped_column(String(32), default="none")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
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


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = uid()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
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
    id: Mapped[str] = uid()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text)
    minio_key: Mapped[str] = mapped_column(Text)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = uid()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    chunk_idx: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(settings.embed_dim))

    __table_args__ = (Index("idx_chunks_tsv", "content"),)


class Ontology(Base):
    __tablename__ = "ontologies"
    id: Mapped[str] = uid()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    entity_types: Mapped[dict] = mapped_column(JSONB)
    relation_types: Mapped[dict] = mapped_column(JSONB)
    seed_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str] = uid()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
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
    id: Mapped[str] = uid()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
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
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    round: Mapped[int] = mapped_column(Integer)
    platform: Mapped[str] = mapped_column(String(32), default="forum")
    seq_in_round: Mapped[int] = mapped_column(Integer)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TokenUsage(Base):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
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


class BreachLog(Base):
    __tablename__ = "security_breach_log"
    id: Mapped[str] = uid()
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str] = mapped_column(Text)
    affected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notified_residents: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_ag: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
