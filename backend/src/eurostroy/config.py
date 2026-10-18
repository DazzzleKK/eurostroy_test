"""Настройки приложения из переменных окружения."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://catalog:catalog@localhost:5432/catalog"
    db_pool_size: int = 5
    db_pool_timeout: float = 10.0

    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "catalog"
    s3_secure: bool = False
    s3_region: str = "us-east-1"

    bot_token: str = ""
    bot_webhook_secret: str = ""
    public_api_url: str = "http://localhost:8000"
    webapp_url: str = "http://localhost:3000"
    admin_ids: str = ""

    page_size_default: int = 20
    page_size_max: int = 100

    @property
    def admins(self) -> frozenset[int]:
        result: set[int] = set()
        for chunk in self.admin_ids.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                result.add(int(chunk))
            except ValueError:
                continue
        return frozenset(result)

    @property
    def webhook_url(self) -> str:
        return f"{self.public_api_url.rstrip('/')}/api/telegram/webhook"

    @property
    def bot_enabled(self) -> bool:
        return bool(self.bot_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
