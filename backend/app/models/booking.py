import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Client(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_clients_tenant_email"),
        Index("idx_clients_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class Booking(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("status IN ('pending_payment', 'confirmed', 'completed', 'cancelled', 'no_show')", name="ck_bookings_status"),
        CheckConstraint("cancelled_by IS NULL OR cancelled_by IN ('client', 'business')", name="ck_bookings_cancelled_by"),
        CheckConstraint("price_status IN ('fixed', 'pending_quote', 'quoted')", name="ck_bookings_price_status"),
        CheckConstraint("deposit_amount >= 0", name="ck_bookings_deposit_amount_nonnegative"),
        CheckConstraint("quoted_price IS NULL OR quoted_price >= 0", name="ck_bookings_quoted_price_nonnegative"),
        CheckConstraint("end_time > start_time", name="valid_booking_time"),
        UniqueConstraint("tenant_id", "staff_id", "start_time", name="unique_staff_slot"),
        Index("idx_bookings_tenant_id", "tenant_id"),
        Index("idx_bookings_staff_id", "staff_id"),
        Index("idx_bookings_client_id", "client_id"),
        Index("idx_bookings_start_time", "start_time"),
        Index("idx_bookings_status", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, server_default="pending_payment")
    deposit_amount: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    price_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="fixed")
    quoted_price: Mapped[int | None] = mapped_column(Integer)
    client_notes: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class BookingInspoAsset(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "booking_inspo_assets"
    __table_args__ = (
        Index("idx_booking_inspo_assets_booking_id", "booking_id"),
        Index("idx_booking_inspo_assets_tenant_id", "tenant_id"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
