"""Social Simulation API configuration (12-factor, env-first)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # app
    secret_key: str = "dev-only-change-me"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 120
    refresh_token_ttl_days: int = 30

    # infra
    database_url: str = "postgresql+psycopg://crowdscope:crowdscope@db:5432/crowdscope"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "crowdscope"
    minio_root_password: str = "crowdscope"
    minio_bucket: str = "crowdscope"
    minio_secure: bool = False
    tei_url: str = "http://tei:80"
    embed_dim: int = 1024
    metrics_port: int = 0

    # LLM (OpenRouter - the only external service)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_monthly_cap_usd: float = 50.0
    llm_mock_mode: bool = False

    # stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    stripe_monthly_price_id: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_credit_5m: str = ""
    public_base_url: str = "http://localhost:3900"

    # engine guards
    engine_max_agents: int = 300
    engine_max_rounds: int = 80
    engine_default_concurrency: int = 30

    # bootstrap admin
    first_admin_email: str = ""
    first_admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
