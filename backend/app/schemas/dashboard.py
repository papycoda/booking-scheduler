from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer
from app.services.settlement_service import mask_account_number


class DashboardBookingResponse(BaseModel):
    id: UUID
    payment_id: UUID | None = None
    status: str
    start_time: datetime
    end_time: datetime
    client_name: str
    client_email: str
    service_name: str
    staff_name: str
    amount: int | None = None
    payment_status: str | None = None
    collection_mode: str | None = None
    platform_fee_amount: int | None = None
    business_net_amount: int | None = None
    settlement_status: str | None = None
    deposit_amount: int
    price_status: str
    quoted_price: int | None = None
    client_notes: str | None = None
    cancellation_reason: str | None = None
    cancelled_by: str | None = None
    inspo_assets: list[dict[str, str | int]] = Field(default_factory=list)


class DashboardBookingStatusUpdate(BaseModel):
    status: str = Field(pattern="^(completed|cancelled|no_show)$")
    cancellation_reason: str | None = None
    quoted_price: int | None = Field(default=None, ge=0)


class DashboardRescheduleRequestResponse(BaseModel):
    id: UUID
    booking_id: UUID
    status: str
    client_name: str
    client_email: str
    service_name: str
    current_staff_name: str
    requested_staff_name: str
    current_start_time: datetime
    current_end_time: datetime
    requested_start_time: datetime
    requested_end_time: datetime
    hold_expires_at: datetime
    client_note: str | None = None
    decision_note: str | None = None


class DashboardRescheduleDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=500)


class DashboardPayoutResponse(BaseModel):
    payment_id: UUID
    settlement_status: str
    payout_transfer_reference: str | None = None
    payout_transfer_code: str | None = None


class DashboardPayoutDetailResponse(BaseModel):
    payment_id: UUID
    booking_id: UUID
    client_name: str
    service_name: str
    amount: int
    platform_fee_amount: int
    business_net_amount: int
    settlement_status: str
    payout_attempt_count: int = 0
    payout_review_reason: str | None = None
    last_payout_error: str | None = None
    next_payout_attempt_at: datetime | None = None
    payout_transfer_reference: str | None = None
    payout_account_name: str | None = None
    payout_bank_name: str | None = None
    masked_payout_account_number: str | None = None

    @field_serializer('masked_payout_account_number')
    def serialize_masked_account(self, value: str | None, _info) -> str | None:
        return mask_account_number(value)


class AnalyticsOverviewResponse(BaseModel):
    from_date: date
    to_date: date
    bookings_count: int
    revenue: int
    top_services: list[dict[str, int | str]]
