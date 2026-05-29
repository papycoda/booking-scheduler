from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardBookingResponse(BaseModel):
    id: UUID
    status: str
    start_time: datetime
    end_time: datetime
    client_name: str
    client_email: str
    service_name: str
    staff_name: str
    amount: int | None = None
    payment_status: str | None = None
    deposit_amount: int
    price_status: str
    quoted_price: int | None = None
    client_notes: str | None = None
    inspo_assets: list[dict[str, str | int]] = Field(default_factory=list)


class DashboardBookingStatusUpdate(BaseModel):
    status: str = Field(pattern="^(completed|cancelled|no_show)$")
    cancellation_reason: str | None = None
    quoted_price: int | None = Field(default=None, ge=0)


class AnalyticsOverviewResponse(BaseModel):
    from_date: date
    to_date: date
    bookings_count: int
    revenue: int
    top_services: list[dict[str, int | str]]
