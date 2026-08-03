from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "CareerOS API"
    app_env: Environment = Field(default="development", validation_alias="APP_ENV")
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:3000"], validation_alias="CORS_ORIGINS")
    log_level: str = "INFO"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/careeros",
        validation_alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, validation_alias="SQL_ECHO")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    redis_key_prefix: str = Field(default="careeros", validation_alias="REDIS_KEY_PREFIX")
    cache_default_ttl_seconds: int = Field(
        default=300,
        validation_alias="CACHE_DEFAULT_TTL_SECONDS",
    )
    session_ttl_seconds: int = Field(default=604800, validation_alias="SESSION_TTL_SECONDS")
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=120, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_WINDOW_SECONDS",
    )
    jwt_secret_key: str = Field(
        default="change-me-in-production",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )
    worker_queue_name: str = Field(default="default", validation_alias="WORKER_QUEUE_NAME")
    worker_poll_interval_seconds: float = Field(
        default=1.0,
        validation_alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    worker_max_retries: int = Field(default=3, validation_alias="WORKER_MAX_RETRIES")
    worker_retry_delay_seconds: int = Field(
        default=30,
        validation_alias="WORKER_RETRY_DELAY_SECONDS",
    )
    worker_result_ttl_seconds: int = Field(
        default=86400,
        validation_alias="WORKER_RESULT_TTL_SECONDS",
    )
    worker_scheduled_poll_interval_seconds: float = Field(
        default=5.0,
        validation_alias="WORKER_SCHEDULED_POLL_INTERVAL_SECONDS",
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    ai_provider: str = Field(default="openai", validation_alias="AI_PROVIDER")
    ai_model: str = Field(default="gpt-4.1-mini", validation_alias="AI_MODEL")
    ai_timeout_seconds: float = Field(default=30.0, validation_alias="AI_TIMEOUT_SECONDS")
    ai_max_retries: int = Field(default=2, validation_alias="AI_MAX_RETRIES")
    ai_temperature: float = Field(default=0.2, validation_alias="AI_TEMPERATURE")
    ai_max_output_tokens: int | None = Field(default=None, validation_alias="AI_MAX_OUTPUT_TOKENS")
    ai_log_prompts: bool = Field(default=False, validation_alias="AI_LOG_PROMPTS")
    ai_input_token_cost_per_1m: float = Field(
        default=0.0,
        validation_alias="AI_INPUT_TOKEN_COST_PER_1M",
    )
    ai_output_token_cost_per_1m: float = Field(
        default=0.0,
        validation_alias="AI_OUTPUT_TOKEN_COST_PER_1M",
    )
    agent_max_retries: int = Field(default=2, validation_alias="AGENT_MAX_RETRIES")
    agent_retry_delay_seconds: float = Field(
        default=1.0,
        validation_alias="AGENT_RETRY_DELAY_SECONDS",
    )
    agent_worker_task_name: str = Field(
        default="agent_execution",
        validation_alias="AGENT_WORKER_TASK_NAME",
    )
    email_daily_limit_per_user: int = Field(
        default=50,
        validation_alias="EMAIL_DAILY_LIMIT_PER_USER",
    )
    email_cooldown_seconds: int = Field(
        default=60,
        validation_alias="EMAIL_COOLDOWN_SECONDS",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_url(self) -> str | None:
        return None if self.is_production else "/docs"

    @property
    def redoc_url(self) -> str | None:
        return None if self.is_production else "/redoc"

    @property
    def openapi_url(self) -> str | None:
        return None if self.is_production else "/openapi.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
