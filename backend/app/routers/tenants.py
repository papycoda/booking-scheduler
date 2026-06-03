from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import PayoutSetupRequest, PaystackOnboardingRequest, PaystackStatusResponse, TenantResponse, TenantUpdateRequest
from app.services.auth_service import slugify_business_name
from app.services.paystack_service import PaystackError, create_subaccount, create_transfer_recipient, resolve_bank_code

router = APIRouter(prefix="/tenants", tags=["tenants"])


async def get_current_tenant(db: AsyncSession, user: User) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "TENANT_NOT_FOUND", "message": "Tenant was not found."},
        )
    return tenant


@router.get("/me", response_model=TenantResponse)
async def read_current_tenant(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    return await get_current_tenant(db, current_user)


@router.patch("/me", response_model=TenantResponse)
async def update_current_tenant(
    payload: TenantUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    tenant = await get_current_tenant(db, current_user)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data:
        requested_slug = slugify_business_name(str(data.pop("slug")))
        if requested_slug != tenant.slug:
            existing = await db.execute(select(Tenant.id).where(Tenant.slug == requested_slug, Tenant.id != tenant.id))
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": "SLUG_UNAVAILABLE", "message": "That booking URL is already taken."},
                )
            tenant.slug = requested_slug
    for field, value in data.items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/me/paystack", response_model=PaystackStatusResponse)
async def onboard_paystack(
    payload: PaystackOnboardingRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaystackStatusResponse:
    tenant = await get_current_tenant(db, current_user)
    try:
        data = await create_subaccount(
            business_name=payload.business_name,
            settlement_bank=payload.settlement_bank,
            account_number=payload.account_number,
            percentage_charge=float(tenant.platform_fee_percentage),
        )
    except PaystackError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "PAYSTACK_SUBACCOUNT_FAILED", "message": "Could not create Paystack subaccount."},
        ) from None

    tenant.paystack_subaccount_code = data.get("subaccount_code")
    tenant.paystack_business_name = payload.business_name
    tenant.payout_bank_code = payload.settlement_bank
    tenant.payout_bank_name = payload.settlement_bank
    tenant.payout_account_number = payload.account_number
    tenant.payout_account_name = payload.business_name
    tenant.payment_setup_status = "split_ready" if tenant.paystack_subaccount_code else "bank_added"
    await db.commit()
    return tenant_payment_status(tenant)


@router.post("/me/payout-setup", response_model=PaystackStatusResponse)
async def save_payout_setup(
    payload: PayoutSetupRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaystackStatusResponse:
    tenant = await get_current_tenant(db, current_user)
    bank_input = payload.bank_name or payload.bank_code or ""
    warning_message = None
    verification_failed = False

    try:
        bank_code, bank_name = await resolve_bank_code(bank_input)
    except PaystackError:
        bank_code, bank_name = bank_input, bank_input
        verification_failed = True

    tenant.payout_bank_code = bank_code
    tenant.payout_bank_name = bank_name
    tenant.payout_account_number = payload.account_number
    tenant.payout_account_name = payload.account_name
    try:
        data = await create_transfer_recipient(
            name=payload.account_name or tenant.name,
            bank_code=bank_code,
            account_number=payload.account_number,
        )
        tenant.payout_recipient_code = data.get("recipient_code")
        tenant.payment_setup_status = "bank_added" if tenant.payout_recipient_code else "not_started"
    except PaystackError:
        tenant.payout_recipient_code = None
        tenant.payment_setup_status = "verification_failed"
        verification_failed = True
    await db.commit()

    # Set user-safe warning message if verification failed
    if verification_failed:
        warning_message = "We saved your details, but could not verify this payout account yet. Please check the bank name and account number."

    return tenant_payment_status(tenant, warning_message=warning_message)


@router.get("/me/paystack", response_model=PaystackStatusResponse)
async def paystack_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaystackStatusResponse:
    tenant = await get_current_tenant(db, current_user)
    return tenant_payment_status(tenant)


def tenant_payment_status(tenant: Tenant, warning_message: str | None = None) -> PaystackStatusResponse:
    return PaystackStatusResponse(
        payout_bank_name=getattr(tenant, "payout_bank_name", None),
        payout_account_name=getattr(tenant, "payout_account_name", None),
        masked_payout_account_number=getattr(tenant, "payout_account_number", None),
        payment_setup_status=getattr(tenant, "payment_setup_status", "not_started"),
        payments_enabled=True,
        payout_ready=bool(getattr(tenant, "payout_recipient_code", None) or getattr(tenant, "paystack_subaccount_code", None)),
        onboarded=getattr(tenant, "paystack_subaccount_code", None) is not None,
        warning_message=warning_message,
    )
