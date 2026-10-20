-- CrowdSim schema v1
-- Requires: pgvector extension (pg16 image: pgvector/pgvector)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------- users ----------
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan          TEXT NOT NULL DEFAULT 'free',
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    monthly_token_budget   BIGINT NOT NULL DEFAULT 1000000,
    monthly_token_used     BIGINT NOT NULL DEFAULT 0,
    billing_status         TEXT NOT NULL DEFAULT 'none', -- none|active|past_due|canceled
    stripe_customer_id     TEXT,
    stripe_subscription_id TEXT,
    credit_balance         BIGINT NOT NULL DEFAULT 0,
    billing_period_end     TIMESTAMPTZ,
    usage_period_start     TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billing_events (
    stripe_event_id TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_ledger (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID,
    delta       BIGINT NOT NULL,
    reason      TEXT NOT NULL,
    stripe_ref  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user ON credit_ledger(user_id, created_at);

-- ---------- model_configs (admin-managed, per-task) ----------
CREATE TABLE IF NOT EXISTS model_configs (
    task_key        TEXT PRIMARY KEY,           -- e.g. agent_act, persona_synth...
    model           TEXT NOT NULL,              -- openrouter model id
    fallbacks       TEXT[] NOT NULL DEFAULT '{}',
    max_tokens      INTEGER NOT NULL,           -- MUST be set; no unbounded output
    temperature     REAL   NOT NULL DEFAULT 0.7,
    top_p           REAL,
    rpm             INTEGER NOT NULL DEFAULT 60,   -- requests/min cap
    tpm             BIGINT  NOT NULL DEFAULT 200000,
    daily_budget_tokens   BIGINT NOT NULL DEFAULT 3000000,
    monthly_budget_tokens BIGINT NOT NULL DEFAULT 30000000,
    cost_in_usd_per_mtok  NUMERIC(10,4) NOT NULL DEFAULT 0,
    cost_out_usd_per_mtok NUMERIC(10,4) NOT NULL DEFAULT 0,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- seed defaults; admin edits via panel
INSERT INTO model_configs (task_key, model, fallbacks, max_tokens, temperature, rpm, daily_budget_tokens, cost_in_usd_per_mtok, cost_out_usd_per_mtok)
VALUES
  ('ingest_ontology', 'google/gemini-3.1-flash-lite',       '{openai/gpt-4o-mini}', 4000, 0.3, 20,   200000, 0.25, 1.5),
  ('persona_synth',   'meta-llama/llama-3.1-70b-instruct',  '{openai/gpt-4o-mini}', 2000, 0.7, 60,   1000000, 0.4,  0.4),
  ('agent_act',       'meta-llama/llama-3.1-8b-instruct',   '{openai/gpt-4o-mini}', 700,  0.7, 600,  3000000, 0.05, 0.08),
  ('agent_digest',    'meta-llama/llama-3.1-8b-instruct',   '{}',                   500,  0.3, 600,  1000000, 0.05, 0.08),
  ('analyst_draft',   'google/gemini-3.8-flash',            '{openai/gpt-4o-mini}', 4000, 0.3, 60,   1000000, 0.825, 4.125),
  ('report_outline',  'google/gemini-3.8-flash',            '{openai/gpt-4o-mini}', 2000, 0.3, 20,   200000, 0.825, 4.125),
  ('report_section',  'google/gemini-3.8-flash',            '{openai/gpt-4o-mini}', 4000, 0.5, 20,   500000, 0.825, 4.125),
  ('agent_interview', 'meta-llama/llama-3.1-70b-instruct',  '{openai/gpt-4o-mini}', 1000, 0.5, 30,   500000, 0.4,  0.4)
ON CONFLICT (task_key) DO NOTHING;

-- ---------- templates (admin-managed topic packs; builtins seeded at startup) ----------
CREATE TABLE IF NOT EXISTS templates (
    key         TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    pack        JSONB NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_builtin  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- privacy_requests (DSR audit trail; user/email nulled after processing) ----------
CREATE TABLE IF NOT EXISTS privacy_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID,
    email        TEXT,
    status       TEXT NOT NULL DEFAULT 'pending', -- pending|processing|completed|failed
    note         TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_privacy_status ON privacy_requests(status, requested_at);

-- ---------- projects ----------
CREATE TABLE IF NOT EXISTS projects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    template_key TEXT NOT NULL DEFAULT 'market_research',
    language     TEXT NOT NULL DEFAULT 'tr',
    status       TEXT NOT NULL DEFAULT 'created', -- created|ingesting|ontology|population|running|report|completed|failed
    sim_config   JSONB NOT NULL DEFAULT '{}'::jsonb, -- agents_n, rounds, platforms, profiles...
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);

-- ---------- documents ----------
CREATE TABLE IF NOT EXISTS documents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename   TEXT NOT NULL,
    minio_key  TEXT NOT NULL,
    mime       TEXT,
    size       BIGINT NOT NULL DEFAULT 0,
    sha256     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);

-- ---------- document_chunks ----------
CREATE TABLE IF NOT EXISTS document_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    chunk_idx   INT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(1024),
    tsv         tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON document_chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_vec ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------- ontologies ----------
CREATE TABLE IF NOT EXISTS ontologies (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID UNIQUE NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_types  JSONB NOT NULL,
    relation_types JSONB NOT NULL,
    seed_summary  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- agents ----------
CREATE TABLE IF NOT EXISTS agents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_idx  INT  NOT NULL,
    name       TEXT NOT NULL,
    bio        TEXT,
    persona    TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    platform   TEXT NOT NULL DEFAULT 'forum',
    memory     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agents_project ON agents(project_id, agent_idx);

-- ---------- runs ----------
CREATE TABLE IF NOT EXISTS runs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'pending', -- pending|running|paused|completed|canceled|failed
    sim_config   JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_round INT NOT NULL DEFAULT 0,
    token_budget BIGINT,
    tokens_used  BIGINT NOT NULL DEFAULT 0,
    cost_usd     NUMERIC(12,4) NOT NULL DEFAULT 0,
    report_object_key TEXT,
    report_meta  JSONB,
    error        TEXT,
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);

-- ---------- run_events (append-only simulation log) ----------
CREATE TABLE IF NOT EXISTS run_events (
    id            BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    round         INT  NOT NULL,
    platform      TEXT NOT NULL DEFAULT 'forum',
    seq_in_round  INT  NOT NULL,
    agent_id      UUID REFERENCES agents(id),
    event_type    TEXT NOT NULL,          -- post|comment|like|repost|digest|system...
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_run ON run_events(run_id, round, seq_in_round);

-- ---------- token_usage (the cost ledger) ----------
CREATE TABLE IF NOT EXISTS token_usage (
    id                BIGSERIAL PRIMARY KEY,
    user_id           UUID,
    project_id        UUID,
    run_id            UUID,
    agent_id          UUID,
    task_key          TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_tokens     INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    cost_usd          NUMERIC(12,6) NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'ok',  -- ok|fallback|failed
    meta              JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_usage_run  ON token_usage(run_id);
CREATE INDEX IF NOT EXISTS idx_usage_time ON token_usage(created_at);

-- ---------- rate limit counters (app-managed, optional persistent view) ----------
CREATE TABLE IF NOT EXISTS security_breach_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detected_at TIMESTAMPTZ NOT NULL,
    scope       TEXT NOT NULL,
    affected_count INT,
    notified_residents TIMESTAMPTZ,
    notified_ag TIMESTAMPTZ,
    notes       TEXT
);
