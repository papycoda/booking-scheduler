from uuid import UUID

from pydantic import BaseModel, Field


class StaffCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    is_bookable: bool = True


class StaffUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    is_bookable: bool | None = None
    is_active: bool | None = None


class StaffResponse(BaseModel):
    id: UUID
    name: str
    bio: str | None = None
    avatar_url: str | None = None
    is_bookable: bool
    is_active: bool

    model_config = {"from_attributes": True}


class StaffServiceAssignmentRequest(BaseModel):
    service_ids: list[UUID]
