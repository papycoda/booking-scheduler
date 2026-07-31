from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WhatsAppConversationSummary(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_phone: str
    customer_name: str | None = None
    state: str
    status: str
    summary: str | None = None
    last_message_at: datetime | None = None
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None
    booking_id: UUID | None = None
    assigned_user_id: UUID | None = None


class WhatsAppMessageResponse(BaseModel):
    id: UUID
    direction: str
    author_type: str
    body: str
    status: str
    provider_message_id: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class WhatsAppConversationDetail(WhatsAppConversationSummary):
    booking_context: dict[str, object] = Field(default_factory=dict)
    messages: list[WhatsAppMessageResponse] = Field(default_factory=list)


class WhatsAppReplyRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class WhatsAppReplyResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    status: str
