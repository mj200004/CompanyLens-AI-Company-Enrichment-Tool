from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.utils import normalize_database_url, parse_bool


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "companylens.db"


class ConfigError(RuntimeError):
    """Raised when the application configuration is invalid."""


@dataclass(slots=True)
class Settings:
    environment: str
    debug: bool
    testing: bool
    secret_key: str
    database_url: str
    anthropic_api_key: str | None
    request_timeout: int
    max_fetch_pages: int
    max_page_bytes: int
    scraper_workers: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
        default_db = f"sqlite:///{DEFAULT_SQLITE_PATH}"

        settings = cls(
            environment=environment,
            debug=parse_bool(os.getenv("FLASK_DEBUG"), default=environment == "development"),
            testing=parse_bool(os.getenv("TESTING"), default=False),
            secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
            database_url=normalize_database_url(os.getenv("DATABASE_URL", default_db)),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "12")),
            max_fetch_pages=int(os.getenv("MAX_FETCH_PAGES", "5")),
            max_page_bytes=int(os.getenv("MAX_PAGE_BYTES", "2000000")),
            scraper_workers=int(os.getenv("SCRAPER_WORKERS", "4")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.environment == "production":
            if not self.secret_key or self.secret_key == "dev-secret-change-me":
                raise ConfigError("SECRET_KEY must be set to a strong non-default value in production.")
            if not self.database_url:
                raise ConfigError("DATABASE_URL must be set in production.")

    def to_flask_config(self) -> dict[str, object]:
        return {
            "ENV": self.environment,
            "DEBUG": self.debug,
            "TESTING": self.testing,
            "SECRET_KEY": self.secret_key,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JSON_SORT_KEYS": False,
            "REQUEST_TIMEOUT": self.request_timeout,
            "MAX_FETCH_PAGES": self.max_fetch_pages,
            "MAX_PAGE_BYTES": self.max_page_bytes,
            "SCRAPER_WORKERS": self.scraper_workers,
            "ANTHROPIC_API_KEY": self.anthropic_api_key,
            "LOG_LEVEL": self.log_level,
        }
