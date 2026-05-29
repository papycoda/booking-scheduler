from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AvailabilityScheduleCreateRequest(BaseModel):
    staff_id: UUID | None = None
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def validate_time_range(self) -> "AvailabilityScheduleCreateRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityScheduleUpdateRequest(BaseModel):
    staff_id: UUID | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "AvailabilityScheduleUpdateRequest":
        if self.start_time is not None and self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityScheduleResponse(BaseModel):
    id: UUID
    staff_id: UUID | None = None
    day_of_week: int
    start_time: time
    end_time: time
    is_active: bool

    model_config = {"from_attributes": True}


class AvailabilityOverrideCreateRequest(BaseModel):
    staff_id: UUID | None = None
    date: date
    is_unavailable: bool = False
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_override(self) -> "AvailabilityOverrideCreateRequest":
        if not self.is_unavailable:
            if self.start_time is None or self.end_time is None or self.end_time <= self.start_time:
                raise ValueError("available overrides require start_time before end_time")
        return self


class AvailabilityOverrideResponse(BaseModel):
    id: UUID
    staff_id: UUID | None = None
    date: date
    is_unavailable: bool
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = None

    model_config = {"from_attributes": True}
