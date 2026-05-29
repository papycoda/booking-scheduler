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


class PublicBookingStatusResponse(BaseModel):
    booking_id: UUID
    booking_status: str
    payment_status: str | None = None
    reference: str | None = None
    start_time: datetime
    end_time: datetime
    service_name: str
    staff_name: str
    deposit_amount: int
    price_status: str
    quoted_price: int | None = None


class BookingInspoAssetResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    url: str
