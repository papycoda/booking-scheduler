from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services.auth_service import (
    consume_password_reset_token,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    generate_unique_slug,
    get_active_user_by_id,
    get_user_by_email,
    hash_password,
    verify_password,
)
from app.services.notification_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.environment == "production",
        samesite="strict",
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegisterResponse:
    existing_user = await get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "EMAIL_ALREADY_REGISTERED", "message": "An account already exists for this email."},
        )

    slug = await generate_unique_slug(db, payload.business_name)
    tenant = Tenant(slug=slug, name=payload.business_name, status="active")
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="tenant_owner",
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "REGISTRATION_CONFLICT", "message": "Tenant slug or email already exists."},
        ) from None

    await db.refresh(tenant)
    await db.refresh(user)
    access_token = create_access_token(user)
    set_refresh_cookie(response, create_refresh_token(user))
    return RegisterResponse(access_token=access_token, tenant_id=tenant.id, user_id=user.id, slug=tenant.slug)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    user = await get_user_by_email(db, payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_CREDENTIALS", "message": "Email or password is incorrect."},
        )

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    access_token = create_access_token(user)
    set_refresh_cookie(response, create_refresh_token(user))
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "REFRESH_TOKEN_MISSING", "message": "Refresh token cookie is missing."},
        )

    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise JWTError("not a refresh token")
        user_id = UUID(str(payload["sub"]))
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired."},
        ) from None

    user = await get_active_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_REFRESH_TOKEN", "message": "Refresh token user is inactive or missing."},
        )
    return TokenResponse(access_token=create_access_token(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    response.delete_cookie(key="refresh_token", httponly=True, secure=settings.environment == "production", samesite="strict")
    return response


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    user = await get_user_by_email(db, payload.email)
    if user is not None and user.is_active:
        token = await create_password_reset_token(user)
        reset_url = f"{str(settings.frontend_url).rstrip('/')}/reset-password?token={token}"
        await send_password_reset_email(to_email=user.email, reset_url=reset_url)
    return {"status": "ok"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    user_id = await consume_password_reset_token(payload.token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_RESET_TOKEN", "message": "Reset token is invalid or expired."},
        )
    user = await get_active_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_RESET_TOKEN", "message": "Reset token is invalid or expired."},
        )
    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"status": "ok"}
