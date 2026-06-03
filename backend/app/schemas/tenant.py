from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator, field_serializer
from app.services.settlement_service import mask_account_number


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None
    logo_url: str | None = None
    timezone: str
    phone: str | None = None
    address: str | None = None
    payout_bank_name: str | None = None
    payout_account_name: str | None = None
    payment_setup_status: str = "not_started"
    platform_fee_percentage: Decimal
    allow_staff_selection: bool
    booking_buffer_minutes: int
    default_deposit_amount: int
    advance_booking_days: int
    min_notice_hours: int
    cancellation_notice_hours: int
    status: str
    masked_payout_account_number: str | None = None

    @field_serializer('masked_payout_account_number')
    def serialize_masked_account(self, value: str | None, _info) -> str | None:
        # When using from_attributes, this receives the raw payout_account_number from the model
        return mask_account_number(value)

    model_config = {"from_attributes": True}

    @classmethod
    def from_tenant(cls, tenant: "Tenant") -> "TenantResponse":
        """Create response from tenant model with masked account number."""
        data = {
            "id": tenant.id,
            "slug": tenant.slug,
            "name": tenant.name,
            "description": tenant.description,
            "logo_url": tenant.logo_url,
            "timezone": tenant.timezone,
            "phone": tenant.phone,
            "address": tenant.address,
            "payout_bank_name": tenant.payout_bank_name,
            "payout_account_name": tenant.payout_account_name,
            "payment_setup_status": tenant.payment_setup_status,
            "platform_fee_percentage": tenant.platform_fee_percentage,
            "allow_staff_selection": tenant.allow_staff_selection,
            "booking_buffer_minutes": tenant.booking_buffer_minutes,
            "default_deposit_amount": tenant.default_deposit_amount,
            "advance_booking_days": tenant.advance_booking_days,
            "min_notice_hours": tenant.min_notice_hours,
            "cancellation_notice_hours": tenant.cancellation_notice_hours,
            "status": tenant.status,
            "masked_payout_account_number": tenant.payout_account_number,
        }
        return cls(**data)


class TenantUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=100)
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


class PayoutSetupRequest(BaseModel):
    bank_code: str | None = Field(default=None, min_length=2, max_length=20)
    bank_name: str | None = Field(default=None, min_length=2, max_length=100)
    account_number: str = Field(pattern=r"^[0-9]{10}$")
    account_name: str | None = Field(default=None, min_length=2, max_length=255)

    @model_validator(mode="after")
    def require_bank_identifier(self) -> "PayoutSetupRequest":
        if not self.bank_code and not self.bank_name:
            raise ValueError("bank_name is required")
        return self


class PaystackStatusResponse(BaseModel):
    payout_bank_name: str | None = None
    payout_account_name: str | None = None
    masked_payout_account_number: str | None = None
    payment_setup_status: str = "not_started"
    payments_enabled: bool = True
    payout_ready: bool = False
    onboarded: bool
    warning_message: str | None = None

    @field_serializer('masked_payout_account_number')
    def serialize_masked_account(self, value: str | None, _info) -> str | None:
        return mask_account_number(value)
