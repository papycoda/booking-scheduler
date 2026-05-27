import uuid

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'pending')",
            name="check_tenant_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50), default="Africa/Lagos")
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    paystack_subaccount_code: Mapped[str | None] = mapped_column(String(100))
    paystack_business_name: Mapped[str | None] = mapped_column(String(255))
    platform_fee_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=5.00,
        nullable=False,
    )
    allow_staff_selection: Mapped[bool] = mapped_column(Boolean, default=True)
    booking_buffer_minutes: Mapped[int] = mapped_column(Integer, default=15)
    advance_booking_days: Mapped[int] = mapped_column(Integer, default=30)
    min_notice_hours: Mapped[int] = mapped_column(Integer, default=2)
    cancellation_notice_hours: Mapped[int] = mapped_column(Integer, default=24)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[object] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
