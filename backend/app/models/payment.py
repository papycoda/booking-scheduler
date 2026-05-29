import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Payment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'success', 'failed', 'refunded')", name="ck_payments_status"),
        CheckConstraint("payment_type IN ('deposit', 'full')", name="ck_payments_payment_type"),
        Index("idx_payments_booking_id", "booking_id"),
        Index("idx_payments_paystack_reference", "paystack_reference"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="NGN")
    paystack_reference: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    paystack_access_code: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="deposit")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
