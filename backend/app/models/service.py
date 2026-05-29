import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Table, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import Column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

staff_services = Table(
    "staff_services",
    Base.metadata,
    Column("staff_id", UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Service(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_services_duration_positive"),
        CheckConstraint("price >= 0", name="ck_services_price_nonnegative"),
        CheckConstraint("pricing_mode IN ('fixed', 'from', 'consultation')", name="ck_services_pricing_mode"),
        CheckConstraint("deposit_policy IN ('tenant_default', 'custom', 'disabled')", name="ck_services_deposit_policy"),
        CheckConstraint("deposit_amount IS NULL OR deposit_amount >= 0", name="ck_services_deposit_amount_nonnegative"),
        Index("idx_services_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="NGN")
    pricing_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="fixed")
    deposit_policy: Mapped[str] = mapped_column(String(20), nullable=False, server_default="tenant_default")
    deposit_amount: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
