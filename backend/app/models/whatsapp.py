import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class WhatsAppConversation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'human_active', 'closed')", name="ck_whatsapp_conversations_status"),
        CheckConstraint(
            "state IN ('collecting_booking_details', 'awaiting_time_choice', 'awaiting_checkout_email', 'awaiting_atomic_confirmation', 'payment_link_pending', 'handoff_pending', 'human_active', 'closed')",
            name="ck_whatsapp_conversations_state",
        ),
        UniqueConstraint("tenant_id", "customer_phone", name="uq_whatsapp_conversations_tenant_phone"),
        Index("idx_whatsapp_conversations_tenant_id", "tenant_id"),
        Index("idx_whatsapp_conversations_last_message_at", "last_message_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    state: Mapped[str] = mapped_column(String(50), nullable=False, server_default="collecting_booking_details")
    summary: Mapped[str | None] = mapped_column(Text)
    booking_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL"))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    messages = relationship("WhatsAppMessage", back_populates="conversation", cascade="all, delete-orphan")


class WhatsAppMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        CheckConstraint("direction IN ('inbound', 'outbound')", name="ck_whatsapp_messages_direction"),
        CheckConstraint("author_type IN ('customer', 'assistant', 'owner', 'system')", name="ck_whatsapp_messages_author_type"),
        CheckConstraint("status IN ('queued', 'sent', 'failed', 'received')", name="ck_whatsapp_messages_status"),
        UniqueConstraint("provider_message_id", name="uq_whatsapp_messages_provider_message_id"),
        Index("idx_whatsapp_messages_conversation_id", "conversation_id"),
        Index("idx_whatsapp_messages_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    author_type: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="received")
    provider_message_id: Mapped[str | None] = mapped_column(String(100))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    conversation = relationship("WhatsAppConversation", back_populates="messages")
