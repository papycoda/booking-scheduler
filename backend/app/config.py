from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = Field(min_length=32)
    frontend_url: AnyHttpUrl
    environment: str = Field(pattern="^(development|production)$")
    database_url: str
    redis_url: str
    paystack_secret_key: str
    paystack_webhook_secret: str | None = None
    resend_api_key: str | None = None
    from_email: str | None = None
    meta_whatsapp_token: str | None = None
    meta_whatsapp_phone_number_id: str | None = None
    meta_whatsapp_business_account_id: str | None = None
    upload_dir: str = "backend/uploads"
    upload_base_url: str = "/uploads"
    max_inspo_images: int = 4
    max_inspo_image_bytes: int = 5 * 1024 * 1024
    max_inspo_total_bytes: int = 15 * 1024 * 1024
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    model_config = SettingsConfigDict(env_file=("backend/.env", ".env"), env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
