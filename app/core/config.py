from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AquaOps"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    database_url: str = "sqlite:///./data/aquaops.db"
    auto_create_tables: bool = True
    session_cookie_name: str = "aquaops_session"
    session_ttl_days: int = 30
    data_dir: Path = PROJECT_ROOT / "data"
    media_root: Path = PROJECT_ROOT / "media"
    static_dir: Path = PROJECT_ROOT / "app" / "web" / "static"
    templates_dir: Path = PROJECT_ROOT / "app" / "web" / "templates"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str) and value.lower() in {"release", "production"}:
            return False
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
