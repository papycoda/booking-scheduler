from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import PaystackOnboardingRequest, PaystackStatusResponse, TenantResponse, TenantUpdateRequest
from app.services.paystack_service import PaystackError, create_subaccount

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
    for field, value in payload.model_dump(exclude_unset=True).items():
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
    await db.commit()
    return PaystackStatusResponse(
        paystack_subaccount_code=tenant.paystack_subaccount_code,
        paystack_business_name=tenant.paystack_business_name,
        onboarded=tenant.paystack_subaccount_code is not None,
    )


@router.get("/me/paystack", response_model=PaystackStatusResponse)
async def paystack_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaystackStatusResponse:
    tenant = await get_current_tenant(db, current_user)
    return PaystackStatusResponse(
        paystack_subaccount_code=tenant.paystack_subaccount_code,
        paystack_business_name=tenant.paystack_business_name,
        onboarded=tenant.paystack_subaccount_code is not None,
    )
