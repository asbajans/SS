"""Bootstrap helpers (idempotent)."""
from pathlib import Path

import structlog
from sqlalchemy import select, text

from app.config import settings
from app.db import AsyncSessionLocal
from app.models import BlogPost, Template, User
from app.security import hash_password
from engine.templates import builtin_templates

log = structlog.get_logger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "init.sql"

_MIGRATIONS = [
    "ALTER TABLE token_usage ADD COLUMN IF NOT EXISTS agent_id UUID",
    """CREATE TABLE IF NOT EXISTS templates (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        pack JSONB NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS privacy_requests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID,
        email TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        note TEXT,
        requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        processed_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS idx_privacy_status ON privacy_requests(status, requested_at)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS credit_balance BIGINT NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS billing_period_end TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS usage_period_start TIMESTAMPTZ",
    """CREATE TABLE IF NOT EXISTS billing_events (
        stripe_event_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS credit_ledger (
        id BIGSERIAL PRIMARY KEY,
        user_id UUID,
        delta BIGINT NOT NULL,
        reason TEXT NOT NULL,
        stripe_ref TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_credit_ledger_user ON credit_ledger(user_id, created_at)",
    """CREATE TABLE IF NOT EXISTS plan_configs (
        key TEXT PRIMARY KEY,
        price_cents INT NOT NULL DEFAULT 0,
        token_budget BIGINT NOT NULL DEFAULT 1000000,
        agents INT NOT NULL DEFAULT 80,
        rounds INT NOT NULL DEFAULT 24,
        free_days INT NOT NULL DEFAULT 0,
        stripe_price_id TEXT NOT NULL DEFAULT '',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INT NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS credit_packs (
        key TEXT PRIMARY KEY,
        tokens BIGINT NOT NULL,
        price_cents INT NOT NULL,
        stripe_price_id TEXT NOT NULL DEFAULT '',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INT NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """INSERT INTO plan_configs (key, price_cents, token_budget, agents, rounds, free_days, sort_order)
       VALUES ('free', 0, 1000000, 80, 24, 0, 0),
              ('starter', 2900, 8000000, 150, 40, 0, 1),
              ('pro', 9900, 25000000, 300, 80, 0, 2)
       ON CONFLICT (key) DO NOTHING""",
    """INSERT INTO credit_packs (key, tokens, price_cents, sort_order)
       VALUES ('credit_5m', 5000000, 1900, 0)
       ON CONFLICT (key) DO NOTHING""",
    """CREATE TABLE IF NOT EXISTS blog_posts (
        slug TEXT PRIMARY KEY,
        title_tr TEXT NOT NULL,
        title_en TEXT NOT NULL,
        excerpt_tr TEXT NOT NULL DEFAULT '',
        excerpt_en TEXT NOT NULL DEFAULT '',
        body_tr TEXT NOT NULL DEFAULT '',
        body_en TEXT NOT NULL DEFAULT '',
        is_published BOOLEAN NOT NULL DEFAULT TRUE,
        published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS api_keys (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL DEFAULT 'default',
        prefix TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        last_used_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        revoked_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)",
    """CREATE TABLE IF NOT EXISTS webhooks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        url TEXT NOT NULL,
        secret TEXT NOT NULL,
        events JSONB NOT NULL DEFAULT '["run.completed","run.failed"]'::jsonb,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        last_attempt_at TIMESTAMPTZ,
        last_status TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhooks(user_id)",
]


async def ensure_schema() -> None:
    if not _SCHEMA_PATH.exists():
        log.warning("schema_file_missing", path=str(_SCHEMA_PATH))
        return
    async with AsyncSessionLocal() as s:
        existing = await s.scalar(select(text("to_regclass('users')")))
        if not existing:
            await s.execute(text(_SCHEMA_PATH.read_text(encoding="utf-8")))
            await s.commit()
            log.info("schema_applied", path=str(_SCHEMA_PATH))
        for stmt in _MIGRATIONS:
            await s.execute(text(stmt))
        await s.commit()


async def seed_templates() -> None:
    async with AsyncSessionLocal() as s:
        added = 0
        for tpl in builtin_templates():
            if await s.get(Template, tpl.key) is None:
                s.add(
                    Template(
                        key=tpl.key,
                        name=tpl.name,
                        description=tpl.description,
                        pack=tpl.to_pack(),
                        is_active=True,
                        is_builtin=True,
                    )
                )
                added += 1
        if added:
            await s.commit()
            log.info("templates_seeded", count=added)


BLOG_POSTS = [
    {
        "slug": "sentetik-topluluk-nedir",
        "title_tr": "Sentetik topluluk nedir ve ne zaman işe yarar?",
        "title_en": "What is a synthetic community and when is it useful?",
        "excerpt_tr": (
            "Gerçek kullanıcıya ulaşmadan önce fikrinizi yüzlerce yapay ajanın "
            "oluşturduğu bir toplulukta test edin."
        ),
        "excerpt_en": (
            "Test your idea with a community of hundreds of synthetic agents "
            "before reaching real users."
        ),
        "body_tr": (
            "Sentetik topluluk, belirli bir konu etrafında tanımlanmış kişiliklere, hafızalara ve "
            "davranış kurallarına sahip yapay ajanların forum benzeri bir ortamda birbiriyle "
            "etkileştiği bir simülasyondur. Amaç gerçek insanları taklit etmek değil; bir mesajın, "
            "ürünün veya politikanın farklı kesimlerde nasıl karşılanabileceğine dair hızlı ve "
            "denetlenebilir bir sinyal üretmektir.\n\n"
            "## Nerede işe yarar?\n\n"
            "- Lansman öncesi mesaj ve konumlandırma testleri\n"
            "- Fiyat ve paket algısının karşılaştırılması\n"
            "- Kriz senaryolarında söylem ve güven dinamikleri\n"
            "- Ürün konseptlerinde özellik önceliklendirme\n\n"
            "## Nerede sınırlıdır?\n\n"
            "Simülasyon çıktısı gerçek anket veya kamuoyu ölçümü değildir. Sonuçlar bir karar "
            "destek katmanı olarak okunmalı; kritik kararlar gerçek kullanıcı araştırmasıyla "
            "doğrulanmalıdır. Raporlarımız bu sınırı her sayfada açıkça belirtir.\n\n"
            "## Neden şimdi?\n\n"
            "Klasik araştırma haftalar sürerken sentetik topluluk saatler içinde ilk sinyali verir. "
            "Doğru kurgulanmış bir simülasyon, araştırma bütçesini nereye harcayacağınızı "
            "netleştirir."
        ),
        "body_en": (
            "A synthetic community is a simulation where artificial agents with defined "
            "personalities, memories and behavior rules interact in a forum-like environment "
            "around a topic. The goal is not to imitate real people, but to produce a fast and "
            "auditable signal about how a message, product or policy may be received by different "
            "segments.\n\n"
            "## Where it helps\n\n"
            "- Pre-launch message and positioning tests\n"
            "- Comparing price and package perception\n"
            "- Discourse and trust dynamics in crisis scenarios\n"
            "- Feature prioritization for product concepts\n\n"
            "## Where it is limited\n\n"
            "Simulation output is not a real poll or public opinion measurement. Results should "
            "be read as a decision-support layer and validated with real user research for "
            "critical decisions. Our reports state this boundary on every page.\n\n"
            "## Why now?\n\n"
            "Classic research takes weeks while a synthetic community gives a first signal within "
            "hours. A well-designed simulation clarifies where to spend your research budget."
        ),
    },
    {
        "slug": "simulasyon-raporu-nasil-okunur",
        "title_tr": "Simülasyon raporu nasıl okunur?",
        "title_en": "How to read a simulation report",
        "excerpt_tr": "Raporu bir kehanet değil, karar destek katmanı olarak okumanın üç adımı.",
        "excerpt_en": "Three steps to read the report as a decision-support layer, not a prophecy.",
        "body_tr": (
            "Her simülasyon raporu aynı iskeleti izler: yönetici özeti, ana bulgular, segment "
            "tepkileri, söylem haritası ve kaynakça. Raporu okurken üç soruya odaklanın.\n\n"
            "## 1. Hangi varsayımlar kurgulandı?\n\n"
            "Ajan popülasyonu, persona alanları ve ontoloji raporun temel varsayımlarıdır. "
            "Sonuçları değerlendirirken bu varsayımların gerçek hedef kitlenizle ne kadar "
            "örtüştüğünü kontrol edin.\n\n"
            "## 2. Hangi sinyaller tekrar ediyor?\n\n"
            "Tek bir ajanın söylediği ilginç bir cümle değil, farklı segmentlerde tekrar eden "
            "örüntüler önemlidir. Rapor bu örüntüleri alıntı ve olay kayıtlarıyla birlikte sunar.\n\n"
            "## 3. Bir sonraki gerçek test ne olmalı?\n\n"
            "Simülasyonun en değerli çıktısı, gerçek kullanıcıyla yapılacak bir sonraki testi "
            "netleştirmesidir. Raporun sonundaki öneriler bu geçişi kolaylaştırır.\n\n"
            "Sonuç olarak raporu bir kehanet gibi değil, hipotez üreten bir araştırma aracı "
            "olarak okuyun. Simülasyon etiketi bunun içindir."
        ),
        "body_en": (
            "Every simulation report follows the same structure: executive summary, key findings, "
            "segment reactions, discourse map and references. Focus on three questions while "
            "reading.\n\n"
            "## 1. Which assumptions were modeled?\n\n"
            "The agent population, persona fields and ontology are the report's core assumptions. "
            "Check how well they match your real audience before evaluating the results.\n\n"
            "## 2. Which signals repeat?\n\n"
            "What matters is not a single agent's interesting sentence, but patterns that repeat "
            "across segments. The report presents these patterns with quotes and event records.\n\n"
            "## 3. What should the next real test be?\n\n"
            "The most valuable output of a simulation is clarifying the next test with real users. "
            "Recommendations at the end of the report make that transition easier.\n\n"
            "Read the report as a hypothesis-generating research tool, not a prophecy. That is why "
            "the simulation label exists."
        ),
    },
    {
        "slug": "api-ile-simulasyon-otomasyonu",
        "title_tr": "API ile simülasyon otomasyonu",
        "title_en": "Simulation automation with the API",
        "excerpt_tr": "Kendi uygulamanızdan proje oluşturun, simülasyonu başlatın ve raporu otomatik alın.",
        "excerpt_en": "Create projects, start simulations and receive reports from your own app.",
        "body_tr": (
            "Social Simulation API, araştırma akışlarını kendi ürününüze bağlamanız için tasarlandı. "
            "API anahtarınızla proje oluşturabilir, simülasyon başlatabilir ve durum sorgulayabilirsiniz.\n\n"
            "## Temel akış\n\n"
            "- `POST /api/v1/projects` ile şablon ve simülasyon ayarlarını gönderin\n"
            "- `POST /api/v1/projects/{id}/runs` ile simülasyonu kuyruğa alın\n"
            "- `GET /api/v1/runs/{id}` ile durumu izleyin\n"
            "- `GET /api/v1/runs/{id}/report/download` ile PDF veya Markdown raporu indirin\n\n"
            "## Webhook ile otomasyon\n\n"
            "Webhook tanımladığınızda simülasyon tamamlandığında veya başarısız olduğunda "
            "sistem sizi imzalı bir HTTPS isteğiyle bilgilendirir. Böylece raporu indirme adımını "
            "da otomatikleştirebilirsiniz.\n\n"
            "API anahtarları planınızın kota ve limitlerine tabidir. Anahtarlar yalnızca "
            "oluşturulduğu anda gösterilir; sunucumuzda yalnızca geri döndürülemez özeti saklanır."
        ),
        "body_en": (
            "The Social Simulation API is designed to connect research workflows to your product. "
            "With your API key you can create projects, start simulations and query status.\n\n"
            "## Core flow\n\n"
            "- Send template and simulation settings with `POST /api/v1/projects`\n"
            "- Queue a simulation with `POST /api/v1/projects/{id}/runs`\n"
            "- Track status with `GET /api/v1/runs/{id}`\n"
            "- Download PDF or Markdown with `GET /api/v1/runs/{id}/report/download`\n\n"
            "## Automation with webhooks\n\n"
            "When you configure a webhook, the system notifies you with a signed HTTPS request "
            "when a simulation completes or fails. This lets you automate the report download step "
            "as well.\n\n"
            "API keys are subject to your plan's quotas and limits. Keys are shown only once at "
            "creation; only an irreversible hash is stored on our servers."
        ),
    },
]


async def seed_blog() -> None:
    async with AsyncSessionLocal() as s:
        added = 0
        for post in BLOG_POSTS:
            if await s.get(BlogPost, post["slug"]) is None:
                s.add(BlogPost(**post))
                added += 1
        if added:
            await s.commit()
            log.info("blog_seeded", count=added)


async def create_first_admin() -> None:
    if not settings.first_admin_email or not settings.first_admin_password:
        return
    async with AsyncSessionLocal() as s:
        existing = (await s.scalars(select(User).where(User.email == settings.first_admin_email))).first()
        if existing is not None:
            return
        user = User(
            email=settings.first_admin_email,
            password_hash=hash_password(settings.first_admin_password),
            is_admin=True,
            plan="pro",
        )
        s.add(user)
        await s.commit()
        log.info("first_admin_created", email=settings.first_admin_email)
