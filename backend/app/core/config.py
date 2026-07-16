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
    log_level: str = "INFO"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/careeros",
        validation_alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, validation_alias="SQL_ECHO")
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
