import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, SmallInteger, String, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import DATE, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class AvailabilitySchedule(Base):
    __tablename__ = "availability_schedules"

    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="check_availability_schedule_day_of_week"),
        CheckConstraint("end_time > start_time", name="check_availability_schedule_end_after_start"),
        UniqueConstraint("tenant_id", "staff_id", "day_of_week", "start_time", "end_time", name="uq_availability_schedule_slot"),
        Index("idx_availability_schedules_tenant_id", "tenant_id"),
        Index("idx_availability_schedules_staff_id", "staff_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=True)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[object] = mapped_column(Time, nullable=False)
    end_time: Mapped[object] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class AvailabilityOverride(Base):
    __tablename__ = "availability_overrides"

    __table_args__ = (
        CheckConstraint("is_unavailable OR (start_time IS NOT NULL AND end_time IS NOT NULL)", name="check_availability_override_times_when_available"),
        CheckConstraint("end_time IS NULL OR start_time IS NULL OR end_time > start_time", name="check_availability_override_end_after_start"),
        UniqueConstraint("tenant_id", "staff_id", "date", name="uq_availability_override_date"),
        Index("idx_availability_overrides_tenant_id", "tenant_id"),
        Index("idx_availability_overrides_staff_id", "staff_id"),
        Index("idx_availability_overrides_date", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=True)
    date: Mapped[object] = mapped_column(DATE, nullable=False)
    is_unavailable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    start_time: Mapped[object | None] = mapped_column(Time)
    end_time: Mapped[object | None] = mapped_column(Time)
    reason: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
