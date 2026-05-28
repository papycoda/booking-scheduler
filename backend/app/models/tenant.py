import uuid

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    __table_args__ = (
        CheckConstraint("status IN ('active', 'suspended', 'pending')", name="check_tenant_status"),
        CheckConstraint("platform_fee_percentage >= 0 AND platform_fee_percentage <= 100", name="check_tenant_platform_fee_range"),
        CheckConstraint("booking_buffer_minutes >= 0", name="check_tenant_booking_buffer_non_negative"),
        CheckConstraint("advance_booking_days > 0", name="check_tenant_advance_booking_positive"),
        CheckConstraint("min_notice_hours >= 0", name="check_tenant_min_notice_non_negative"),
        CheckConstraint("cancellation_notice_hours >= 0", name="check_tenant_cancellation_notice_non_negative"),
        Index("idx_tenants_status", "status"),
        Index("idx_tenants_slug_trgm", "slug", postgresql_using="gin", postgresql_ops={"slug": "gin_trgm_ops"}),
        Index("idx_tenants_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="Africa/Lagos")
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    paystack_subaccount_code: Mapped[str | None] = mapped_column(String(100), unique=True)
    paystack_business_name: Mapped[str | None] = mapped_column(String(255))
    platform_fee_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, server_default="5.00")
    allow_staff_selection: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    booking_buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    advance_booking_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    min_notice_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    cancellation_notice_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="24")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
