import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"

    __table_args__ = (
        CheckConstraint("recipient_type IN ('client', 'staff', 'tenant')", name="check_notification_recipient_type"),
        CheckConstraint("channel IN ('email', 'whatsapp')", name="check_notification_channel"),
        CheckConstraint("status IN ('pending', 'sent', 'failed')", name="check_notification_status"),
        Index("idx_notification_log_tenant_id", "tenant_id"),
        Index("idx_notification_log_booking_id", "booking_id"),
        Index("idx_notification_log_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)
    recipient_type: Mapped[str] = mapped_column(String(10), nullable=False)
    channel: Mapped[str] = mapped_column(String(15), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[object | None] = mapped_column(TIMESTAMP(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
