from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lucent:lucent@localhost:5432/lucenteval"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://lucent:lucent@localhost:5432/lucenteval"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # S3 / object storage
    S3_BUCKET: str = "lucenteval-responses"
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_REGION: str = "us-east-1"

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_DB: str = "lucenteval"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    # Auth / security
    SECRET_KEY: str = "change-me-in-production-use-32-chars-min"
    API_KEY_PREFIX: str = "lev_"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Rate limiting defaults (requests per minute)
    DEFAULT_RATE_LIMIT_RPM: int = 60

    # Corpus
    CORPUS_VERSION: str = "v1"

    # Scoring weights (v1)
    WEIGHT_ADVERSARIAL: float = 0.25
    WEIGHT_TOOL_MISUSE: float = 0.20
    WEIGHT_HALLUCINATION: float = 0.20
    WEIGHT_RECOVERY: float = 0.15
    WEIGHT_LATENCY: float = 0.10
    WEIGHT_COST: float = 0.10

    # Webhook
    WEBHOOK_MAX_RETRIES: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
