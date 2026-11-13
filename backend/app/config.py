from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL


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

    @property
    def demo_admin_emails_list(self) -> list[str]:
        """Parse and normalize demo admin emails from the config string."""
        if not self.demo_admin_emails:
            return []
        return [email.strip().lower() for email in self.demo_admin_emails.split(",") if email.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        return normalize_async_database_url(self.database_url)[0]

    @property
    def asyncpg_connect_args(self) -> dict[str, bool]:
        return normalize_async_database_url(self.database_url)[1]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()


def normalize_async_database_url(database_url: str) -> tuple[str, dict[str, bool]]:
    """Return an asyncpg URL and connect args for Render-style Postgres URLs."""
    raw = database_url.strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    url = make_url(raw)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    sslmode = str(query.pop("sslmode", "") or "").lower()
    query.pop("channel_binding", None)
    connect_args: dict[str, bool] = {}
    if sslmode == "disable":
        connect_args["ssl"] = False
    elif sslmode:
        connect_args["ssl"] = True
    if query != dict(url.query):
        url = url.set(query=query)
    return _render_database_url(url), connect_args


def _render_database_url(url: URL) -> str:
    return url.render_as_string(hide_password=False)
