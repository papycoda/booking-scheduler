import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.services.redis_service import redis_client

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


def create_access_token(user: User) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
        "type": "access",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(user: User) -> str:
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "role": user.role,
        "type": "refresh",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def slugify_business_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:100] or "business"


async def generate_unique_slug(db: AsyncSession, business_name: str) -> str:
    base_slug = slugify_business_name(business_name)
    slug = base_slug
    suffix = 2
    while True:
        result = await db.execute(select(Tenant.id).where(Tenant.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        suffix_text = f"-{suffix}"
        slug = f"{base_slug[:100 - len(suffix_text)]}{suffix_text}"
        suffix += 1


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
    return result.scalar_one_or_none()


async def get_active_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    return result.scalar_one_or_none()


def hmac_reset_token(token: str) -> str:
    return hmac.new(settings.secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def reset_token_key(token_hash: str) -> str:
    return f"password-reset:{token_hash}"


async def create_password_reset_token(user: User) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hmac_reset_token(token)
    await redis_client.set(reset_token_key(token_hash), str(user.id), ex=3600, nx=True)
    return token


async def consume_password_reset_token(token: str) -> UUID | None:
    token_hash = hmac_reset_token(token)
    key = reset_token_key(token_hash)
    user_id = await redis_client.get(key)
    if user_id is None:
        return None
    await redis_client.delete(key)
    return UUID(user_id)
