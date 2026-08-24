"""Application configuration — all values come from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings loaded from .env / environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Zindagi Blood Donor Network"
    app_version: str = "1.0.0"
    environment: str = "development"

    secret_key: str = "change-me-in-production-please-32-chars-min"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./zindagi.db"

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000,https://*.vercel.app"

    # Rate limiting
    rate_limit_auth: int = 10  # requests per minute for auth endpoints
    rate_limit_general: int = 60

    # Donor eligibility
    min_age: int = 18
    max_age: int = 60
    min_weight_kg: int = 50
    donation_cooldown_days: int = 90

    # Request expiry windows (hours) by urgency
    expiry_normal_hours: int = 72
    expiry_urgent_hours: int = 24
    expiry_emergency_hours: int = 6

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
