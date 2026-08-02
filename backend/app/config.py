from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = Field(min_length=32)
    frontend_url: AnyHttpUrl
    environment: str = Field(pattern="^(development|production)$")
    database_url: str
    redis_url: str
    paystack_secret_key: str
    paystack_webhook_secret: str | None = None
    demo_mode: bool = False
    demo_admin_emails: str = Field(default="")
    resend_api_key: str | None = None
    from_email: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from_number: str | None = None
    whatsapp_ai_provider: str = Field(default="deterministic")
    whatsapp_ai_api_key: str | None = None
    whatsapp_ai_base_url: str | None = None
    whatsapp_ai_model: str | None = None
    upload_dir: str = "backend/uploads"
    upload_base_url: str = "/uploads"
    max_inspo_images: int = 4
    max_inspo_image_bytes: int = 5 * 1024 * 1024
    max_inspo_total_bytes: int = 15 * 1024 * 1024
    image_storage_provider: Literal["database", "cloudinary"] = "database"
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    model_config = SettingsConfigDict(env_file=("backend/.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_provider_and_production_settings(self) -> "Settings":
        has_resend_key = bool((self.resend_api_key or "").strip())
        has_from_email = bool((self.from_email or "").strip())
        if has_resend_key != has_from_email:
            raise ValueError("RESEND_API_KEY and FROM_EMAIL must be configured together.")

        twilio_values = (
            self.twilio_account_sid,
            self.twilio_auth_token,
            self.twilio_whatsapp_from_number,
        )
        configured_twilio_values = sum(bool((value or "").strip()) for value in twilio_values)
        if configured_twilio_values not in (0, len(twilio_values)):
            raise ValueError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM_NUMBER must be configured together."
            )

        cloudinary_values = (
            self.cloudinary_cloud_name,
            self.cloudinary_api_key,
            self.cloudinary_api_secret,
        )
        configured_cloudinary_values = sum(bool((value or "").strip()) for value in cloudinary_values)
        if configured_cloudinary_values not in (0, len(cloudinary_values)):
            raise ValueError(
                "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET must be configured together."
            )
        if self.image_storage_provider == "cloudinary" and configured_cloudinary_values != len(cloudinary_values):
            raise ValueError("Cloudinary credentials are required when IMAGE_STORAGE_PROVIDER=cloudinary.")

        if self.environment != "production":
            return self

        errors: list[str] = []
        if self.demo_mode:
            errors.append("DEMO_MODE must be false in production")
        if str(self.frontend_url).lower().startswith("http://"):
            errors.append("FRONTEND_URL must use HTTPS in production")
        if not self.paystack_secret_key.strip():
            errors.append("PAYSTACK_SECRET_KEY is required in production")
        if not has_resend_key or not has_from_email:
            errors.append("RESEND_API_KEY and FROM_EMAIL are required in production")
        if "change-me" in self.secret_key.lower():
            errors.append("SECRET_KEY must be replaced in production")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @property
    def demo_admin_emails_list(self) -> list[str]:
        """Parse and normalize demo admin emails from the config string."""
        if not self.demo_admin_emails:
            return []
        return [email.strip().lower() for email in self.demo_admin_emails.split(",") if email.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
