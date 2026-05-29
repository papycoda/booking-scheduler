from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.service import ServiceResponse
from app.schemas.staff import StaffResponse


class PublicTenantResponse(BaseModel):
    slug: str
    name: str
    description: str | None = None
    logo_url: str | None = None
    timezone: str
    allow_staff_selection: bool
    advance_booking_days: int


class PublicServiceResponse(ServiceResponse):
    deposit_due_now: int
    price_label: str


class PublicStaffResponse(StaffResponse):
    pass


class SlotQuery(BaseModel):
    service_id: UUID
    staff_id: UUID | None = None
    date: date


class PublicSlotResponse(BaseModel):
    start_time: datetime
    end_time: datetime
