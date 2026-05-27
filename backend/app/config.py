from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    SECRET_KEY: str = Field(min_length=64)
    FRONTEND_URL: str
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    REDIS_URL: str

    PAYSTACK_SECRET_KEY: str
    PAYSTACK_WEBHOOK_SECRET: str

    RESEND_API_KEY: str
    FROM_EMAIL: str

    META_WHATSAPP_TOKEN: str
    META_WHATSAPP_PHONE_NUMBER_ID: str
    META_WHATSAPP_BUSINESS_ACCOUNT_ID: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
