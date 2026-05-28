import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_clients_tenant_email"),
        Index("idx_clients_tenant_id", "tenant_id"),
        Index("idx_clients_email_trgm", "email", postgresql_using="gin", postgresql_ops={"email": "gin_trgm_ops"}),
        Index("idx_clients_full_name_trgm", "full_name", postgresql_using="gin", postgresql_ops={"full_name": "gin_trgm_ops"}),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Booking(Base):
    __tablename__ = "bookings"

    __table_args__ = (
        CheckConstraint("status IN ('pending_payment', 'confirmed', 'cancelled', 'completed', 'no_show')", name="check_booking_status"),
        CheckConstraint("cancelled_by IS NULL OR cancelled_by IN ('client', 'staff', 'system')", name="check_booking_cancelled_by"),
        CheckConstraint("end_time > start_time", name="check_booking_end_after_start"),
        UniqueConstraint("tenant_id", "staff_id", "start_time", name="uq_bookings_tenant_staff_start_time"),
        Index("idx_bookings_tenant_id", "tenant_id"),
        Index("idx_bookings_staff_id", "staff_id"),
        Index("idx_bookings_service_id", "service_id"),
        Index("idx_bookings_client_id", "client_id"),
        Index("idx_bookings_tenant_start_time", "tenant_id", "start_time"),
        Index("idx_bookings_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    start_time: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    end_time: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, server_default="pending_payment")
    client_notes: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[object | None] = mapped_column(TIMESTAMP(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(String(10))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
