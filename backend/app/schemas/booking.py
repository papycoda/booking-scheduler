from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ClientBookingRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")
    whatsapp_number: str | None = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")


class PublicBookingCreateRequest(BaseModel):
    service_id: UUID
    staff_id: UUID | None = None
    start_time: datetime
    client: ClientBookingRequest
    notes: str | None = None

    @model_validator(mode="after")
    def start_time_must_have_timezone(self) -> "PublicBookingCreateRequest":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must include a timezone offset")
        return self


class PublicBookingCreateResponse(BaseModel):
    booking_id: UUID
    payment_url: str
    reference: str
    expires_at: datetime
    deposit_amount: int
    manage_url: str


class PublicBookingStatusResponse(BaseModel):
    booking_id: UUID
    booking_status: str
    payment_status: str | None = None
    reference: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    service_name: str | None = None
    staff_name: str | None = None
    deposit_amount: int | None = None
    price_status: str | None = None
    quoted_price: int | None = None
    manage_url: str | None = None


class PublicRescheduleRequestSummary(BaseModel):
    id: UUID
    status: str
    requested_start_time: datetime
    requested_end_time: datetime
    requested_staff_id: UUID
    staff_name: str | None = None
    hold_expires_at: datetime
    client_note: str | None = None
    decision_note: str | None = None


class PublicManagedBookingResponse(BaseModel):
    booking_id: UUID
    booking_status: str
    payment_status: str | None = None
    start_time: datetime
    end_time: datetime
    service_id: UUID
    service_name: str
    staff_id: UUID
    staff_name: str
    deposit_amount: int
    price_status: str
    quoted_price: int | None = None
    cancellation_deadline: datetime
    can_cancel: bool
    deposit_notice: str = "Deposits are non-refundable."
    pending_reschedule_requests: list[PublicRescheduleRequestSummary] = Field(default_factory=list)


class PublicBookingCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class PublicRescheduleRequestCreate(BaseModel):
    start_time: datetime
    staff_id: UUID | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def start_time_must_have_timezone(self) -> "PublicRescheduleRequestCreate":
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must include a timezone offset")
        return self


class PublicRescheduleRequestResponse(BaseModel):
    id: UUID
    status: str
    requested_start_time: datetime
    requested_end_time: datetime
    requested_staff_id: UUID
    hold_expires_at: datetime
    client_note: str | None = None


class BookingInspoAssetResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    url: str
