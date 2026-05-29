from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None
    logo_url: str | None = None
    timezone: str
    phone: str | None = None
    address: str | None = None
    paystack_subaccount_code: str | None = None
    paystack_business_name: str | None = None
    platform_fee_percentage: Decimal
    allow_staff_selection: bool
    booking_buffer_minutes: int
    default_deposit_amount: int
    advance_booking_days: int
    min_notice_hours: int
    cancellation_notice_hours: int
    status: str

    model_config = {"from_attributes": True}


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")
    address: str | None = None
    allow_staff_selection: bool | None = None
    booking_buffer_minutes: int | None = Field(default=None, ge=0, le=480)
    default_deposit_amount: int | None = Field(default=None, ge=0, le=100_000_000)
    advance_booking_days: int | None = Field(default=None, ge=1, le=365)
    min_notice_hours: int | None = Field(default=None, ge=0, le=720)
    cancellation_notice_hours: int | None = Field(default=None, ge=0, le=720)
    platform_fee_percentage: Decimal | None = Field(default=None, ge=0, le=30)


class PaystackOnboardingRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=255)
    settlement_bank: str = Field(min_length=2, max_length=20)
    account_number: str = Field(pattern=r"^[0-9]{10}$")


class PaystackStatusResponse(BaseModel):
    paystack_subaccount_code: str | None = None
    paystack_business_name: str | None = None
    onboarded: bool
