from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'suspended', 'pending')", name="ck_tenants_status"),
        CheckConstraint("platform_fee_percentage >= 0 AND platform_fee_percentage <= 30", name="ck_tenants_platform_fee_range"),
        CheckConstraint("default_deposit_amount >= 0", name="ck_tenants_default_deposit_nonnegative"),
        Index("idx_tenants_slug", "slug"),
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="Africa/Lagos")
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    paystack_subaccount_code: Mapped[str | None] = mapped_column(String(100))
    paystack_business_name: Mapped[str | None] = mapped_column(String(255))
    platform_fee_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="5.00")
    allow_staff_selection: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    booking_buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    default_deposit_amount: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    advance_booking_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    min_notice_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    cancellation_notice_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default="24")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    users = relationship("User", back_populates="tenant")
