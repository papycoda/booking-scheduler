from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AssistantIntent = Literal[
    "list_services",
    "service_price",
    "service_duration",
    "available_slots",
    "business_location",
    "deposit_policy",
    "cancellation_policy",
    "reschedule_policy",
    "how_to_book",
    "fallback",
]

AssistantActionType = Literal["view_service", "book_now", "show_slots"]


class AssistantContext(BaseModel):
    service_id: UUID | None = None
    selected_date: date | None = None


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    context: AssistantContext | None = None


class AssistantSuggestedAction(BaseModel):
    type: AssistantActionType
    label: str
    service_id: UUID | None = None
    start_time: datetime | None = None


class AssistantResponse(BaseModel):
    reply: str
    intent: AssistantIntent
    suggested_actions: list[AssistantSuggestedAction] = Field(default_factory=list)
