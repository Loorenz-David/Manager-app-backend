from typing import Annotated
import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _resolve_env_file() -> str:
    app_env = (os.getenv("APP_ENV") or "development").strip().lower()
    if app_env == "testing":
        return ".env.testing"
    if app_env == "validation":
        return ".env.validation"
    if app_env == "production":
        return ".env.production"
    return ".env"


class Settings(BaseSettings):
    # Core
    secret_key: str | None = Field(default=None, alias="SECRET_KEY")
    jwt_secret_key: str | None = Field(default=None, alias="JWT_SECRET_KEY")

    # Database - must use asyncpg driver: postgresql+asyncpg://...
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # Redis
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    redis_key_prefix: str = Field(default="beyo_manager", alias="REDIS_KEY_PREFIX")

    # Database pool
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")

    # Request / Performance
    request_timeout_seconds: int = Field(default=30, alias="REQUEST_TIMEOUT_SECONDS")
    slow_query_threshold_ms: int = Field(default=500, alias="SLOW_QUERY_THRESHOLD_MS")
    presence_debounce_seconds: int = Field(default=30, alias="PRESENCE_DEBOUNCE_SECONDS")

    # CORS
    frontend_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173"],
        alias="FRONTEND_ORIGINS",
    )

    # JWT
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=30, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    auth_refresh_cookie_secure: bool | None = Field(default=None, alias="AUTH_REFRESH_COOKIE_SECURE")
    auth_refresh_cookie_samesite: str = Field(default="lax", alias="AUTH_REFRESH_COOKIE_SAMESITE")
    auth_refresh_cookie_path: str = Field(default="/", alias="AUTH_REFRESH_COOKIE_PATH")
    auth_refresh_cookie_domain: str | None = Field(default=None, alias="AUTH_REFRESH_COOKIE_DOMAIN")
    auth_refresh_cookie_max_age_seconds: int | None = Field(default=None, alias="AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS")

    # VAPID (Web Push)
    vapid_private_key:   str | None = Field(default=None, alias="VAPID_PRIVATE_KEY")
    vapid_public_key:    str | None = Field(default=None, alias="VAPID_PUBLIC_KEY")
    vapid_contact_email: str        = Field(default="admin@example.com", alias="VAPID_CONTACT_EMAIL")

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # File storage
    storage_provider: str = Field(default="local", alias="STORAGE_PROVIDER")
    storage_bucket: str | None = Field(default=None, alias="STORAGE_BUCKET")
    storage_region: str | None = Field(default=None, alias="STORAGE_REGION")
    storage_endpoint_url: str | None = Field(default=None, alias="STORAGE_ENDPOINT_URL")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    local_storage_path: str = Field(default="/tmp/beyo_manager-uploads", alias="LOCAL_STORAGE_PATH")
    local_storage_host: str = Field(default="http://localhost:8000", alias="LOCAL_STORAGE_HOST")

    # Idle sleep mode — see 22_performance.md
    sleep_mode_enabled: bool = Field(default=True, alias="SLEEP_MODE_ENABLED")
    idle_sleep_threshold_seconds: int = Field(default=600, alias="IDLE_SLEEP_THRESHOLD_SECONDS")

    # Bootstrap
    bootstrap_secret: str | None = Field(default=None, alias="BOOTSTRAP_SECRET")
    bootstrap_admin_email: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_username: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_password: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_PASSWORD")
    bootstrap_workspace_name: str = Field(default="My Workspace", alias="BOOTSTRAP_WORKSPACE_NAME")
    bootstrap_workspace_timezone: str = Field(default="UTC", alias="BOOTSTRAP_WORKSPACE_TIMEZONE")

    # Reset (development only)
    reset_secret: str = Field(default="", alias="RESET_SECRET")

    model_config = SettingsConfigDict(
        # Load deterministic env profile selected by APP_ENV.
        # APP_ENV can be: development | testing | validation | production.
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="ignore",
    )

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def _require_critical_settings(self):
        self.auth_refresh_cookie_samesite = self.auth_refresh_cookie_samesite.lower().strip()
        if self.auth_refresh_cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_REFRESH_COOKIE_SAMESITE must be one of: lax, strict, none")

        # Default to secure cookies outside local/test profiles.
        if self.auth_refresh_cookie_secure is None:
            self.auth_refresh_cookie_secure = self.environment not in {"development", "testing", "validation"}

        # Browser policy: SameSite=None requires Secure.
        if self.auth_refresh_cookie_samesite == "none" and not self.auth_refresh_cookie_secure:
            raise ValueError("AUTH_REFRESH_COOKIE_SAMESITE=none requires AUTH_REFRESH_COOKIE_SECURE=true")

        required = ["secret_key", "jwt_secret_key", "database_url", "redis_url"]
        missing = [name for name in required if not getattr(self, name)]
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")
        return self


settings = Settings()
