-- CrowdSim schema v1
-- Requires: pgvector extension (pg16 image: pgvector/pgvector)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------- users ----------
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    google_id     TEXT,
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
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user ON credit_ledger(user_id, created_at);

CREATE TABLE IF NOT EXISTS plan_configs (
    key             TEXT PRIMARY KEY,
    price_cents     INT NOT NULL DEFAULT 0,
    token_budget    BIGINT NOT NULL DEFAULT 1000000,
    agents          INT NOT NULL DEFAULT 80,
    rounds          INT NOT NULL DEFAULT 24,
    free_days       INT NOT NULL DEFAULT 0,
    stripe_price_id TEXT NOT NULL DEFAULT '',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_packs (
    key             TEXT PRIMARY KEY,
    tokens          BIGINT NOT NULL,
    price_cents     INT NOT NULL,
    stripe_price_id TEXT NOT NULL DEFAULT '',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO plan_configs (key, price_cents, token_budget, agents, rounds, free_days, sort_order)
VALUES ('free', 0, 1000000, 80, 24, 0, 0),
       ('starter', 2900, 8000000, 150, 40, 0, 1),
       ('pro', 9900, 25000000, 300, 80, 0, 2)
ON CONFLICT (key) DO NOTHING;

INSERT INTO credit_packs (key, tokens, price_cents, sort_order)
VALUES ('credit_5m', 5000000, 1900, 0)
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS blog_posts (
    slug         TEXT PRIMARY KEY,
    title_tr     TEXT NOT NULL,
    title_en     TEXT NOT NULL,
    excerpt_tr   TEXT NOT NULL DEFAULT '',
    excerpt_en   TEXT NOT NULL DEFAULT '',
    body_tr      TEXT NOT NULL DEFAULT '',
    body_en      TEXT NOT NULL DEFAULT '',
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    meta_description_tr TEXT NOT NULL DEFAULT '',
    meta_description_en TEXT NOT NULL DEFAULT '',
    focus_keyword_tr    VARCHAR(160) NOT NULL DEFAULT '',
    focus_keyword_en    VARCHAR(160) NOT NULL DEFAULT '',
    og_image            VARCHAR(512) NOT NULL DEFAULT '',
    canonical_url       VARCHAR(512) NOT NULL DEFAULT '',
    noindex             BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS blog_topics (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic        TEXT NOT NULL,
    keywords     TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'queued',
    post_slug    TEXT REFERENCES blog_posts(slug) ON DELETE SET NULL,
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_blog_topics_status ON blog_topics(status, created_at);

CREATE TABLE IF NOT EXISTS blog_automation (
    id           INT PRIMARY KEY DEFAULT 1,
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    interval_days INT NOT NULL DEFAULT 7,
    next_run_at  TIMESTAMPTZ,
    last_run_at  TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seo_settings (
    id                      INT PRIMARY KEY DEFAULT 1,
    site_name               TEXT NOT NULL DEFAULT 'Social Simulator',
    site_url                TEXT NOT NULL DEFAULT '',
    title_suffix            TEXT NOT NULL DEFAULT '',
    default_description_tr  TEXT NOT NULL DEFAULT '',
    default_description_en  TEXT NOT NULL DEFAULT '',
    og_image                TEXT NOT NULL DEFAULT '',
    twitter_site            TEXT NOT NULL DEFAULT '',
    robots_extra            TEXT NOT NULL DEFAULT '',
    block_ai_bots           BOOLEAN NOT NULL DEFAULT FALSE,
    allow_ai_bots           TEXT NOT NULL DEFAULT 'GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot',
    llms_txt                TEXT NOT NULL DEFAULT '',
    google_site_verification TEXT NOT NULL DEFAULT '',
    bing_site_verification  TEXT NOT NULL DEFAULT '',
    indexnow_enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    indexnow_key            TEXT NOT NULL DEFAULT '',
    indexnow_endpoint       TEXT NOT NULL DEFAULT 'https://api.indexnow.org/indexnow',
    analytics_enabled       BOOLEAN NOT NULL DEFAULT FALSE,
    analytics_provider      TEXT NOT NULL DEFAULT 'ga4',
    analytics_id            TEXT NOT NULL DEFAULT '',
    analytics_domain        TEXT NOT NULL DEFAULT '',
    ads_enabled             BOOLEAN NOT NULL DEFAULT FALSE,
    adsense_client          TEXT NOT NULL DEFAULT '',
    adsense_slot            TEXT NOT NULL DEFAULT '',
    adsense_slot_secondary  TEXT NOT NULL DEFAULT '',
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seo_pages (
    path             TEXT PRIMARY KEY,
    title_tr         TEXT NOT NULL DEFAULT '',
    title_en         TEXT NOT NULL DEFAULT '',
    description_tr   TEXT NOT NULL DEFAULT '',
    description_en   TEXT NOT NULL DEFAULT '',
    og_image         TEXT NOT NULL DEFAULT '',
    canonical_url    TEXT NOT NULL DEFAULT '',
    focus_keyword    TEXT NOT NULL DEFAULT '',
    noindex          BOOLEAN NOT NULL DEFAULT FALSE,
    sitemap_priority NUMERIC(3,2) NOT NULL DEFAULT 0.7,
    changefreq       TEXT NOT NULL DEFAULT 'weekly',
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seo_submissions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url        TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',
    detail     TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seo_submissions_created ON seo_submissions(created_at DESC);

CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT NOT NULL DEFAULT 'default',
    prefix       TEXT NOT NULL,
    key_hash     TEXT NOT NULL UNIQUE,
    last_used_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS webhooks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    secret          TEXT NOT NULL,
    events          JSONB NOT NULL DEFAULT '["run.completed","run.failed"]'::jsonb,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    last_attempt_at TIMESTAMPTZ,
    last_status     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhooks(user_id);

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
  ('agent_interview', 'meta-llama/llama-3.1-70b-instruct',  '{openai/gpt-4o-mini}', 1000, 0.5, 30,   500000, 0.4,  0.4),
  ('blog_editor',     'google/gemini-3.8-flash',            '{openai/gpt-4o-mini}', 6000, 0.6, 20,   500000, 0.825, 4.125)
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
