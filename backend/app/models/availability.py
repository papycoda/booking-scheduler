import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, String, Time, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class AvailabilitySchedule(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "availability_schedules"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_availability_schedules_day_of_week"),
        CheckConstraint("end_time > start_time", name="valid_time_range"),
        Index("idx_avail_schedules_tenant", "tenant_id"),
        Index("idx_avail_schedules_staff", "staff_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class AvailabilityOverride(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "availability_overrides"
    __table_args__ = (
        CheckConstraint(
            "is_unavailable = TRUE OR (start_time IS NOT NULL AND end_time IS NOT NULL AND end_time > start_time)",
            name="valid_override",
        ),
        Index("idx_avail_overrides_tenant_date", "tenant_id", "date"),
        Index("idx_avail_overrides_staff_date", "staff_id", "date"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_unavailable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
