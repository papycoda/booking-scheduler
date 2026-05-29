import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class NotificationLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        CheckConstraint("recipient_type IN ('client', 'staff', 'owner')", name="ck_notification_log_recipient_type"),
        CheckConstraint("channel IN ('email', 'whatsapp', 'sms')", name="ck_notification_log_channel"),
        CheckConstraint(
            "type IN ('booking_confirmation', 'booking_reminder_24h', 'booking_reminder_1h', 'booking_cancellation', 'booking_rescheduled')",
            name="ck_notification_log_type",
        ),
        CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_notification_log_status"),
        Index("idx_notif_log_booking_id", "booking_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"))
    recipient_type: Mapped[str] = mapped_column(String(10), nullable=False)
    channel: Mapped[str] = mapped_column(String(15), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
