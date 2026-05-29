from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Iterable
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import AvailabilityOverride, AvailabilitySchedule
from app.models.booking import Booking
from app.models.service import Service, staff_services
from app.models.staff import Staff
from app.models.tenant import Tenant


@dataclass(frozen=True)
class AvailableSlot:
    start_time: datetime
    end_time: datetime
    available_staff: tuple[UUID, ...]


@dataclass(frozen=True)
class LocalWindow:
    start_time: time
    end_time: time


async def generate_available_slots(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    service_id: UUID,
    requested_date: date,
    staff_id: UUID | None = None,
    now: datetime | None = None,
) -> list[AvailableSlot]:
    tenant = await load_tenant(db, tenant_id)
    service = await load_service(db, tenant_id, service_id)
    validate_requested_date(tenant, requested_date, now)
    candidate_staff = await load_candidate_staff(db, tenant_id=tenant_id, service_id=service_id, staff_id=staff_id)

    merged: dict[datetime, tuple[datetime, set[UUID]]] = {}
    tenant_zone = ZoneInfo(tenant.timezone)
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    minimum_start = current_time.astimezone(UTC) + timedelta(hours=tenant.min_notice_hours)

    for staff_member in candidate_staff:
        windows = await load_working_windows(db, tenant_id, staff_member.id, requested_date)
        if not windows:
            continue
        bookings = await load_bookings_for_local_date(db, tenant_id, staff_member.id, requested_date, tenant_zone)
        for window in windows:
            for start_utc, end_utc in iter_candidate_slots(
                requested_date=requested_date,
                window=window,
                tenant_zone=tenant_zone,
                duration_minutes=service.duration_minutes,
                buffer_minutes=tenant.booking_buffer_minutes,
            ):
                if start_utc < minimum_start:
                    continue
                if any(overlaps(start_utc, end_utc, booking.start_time, booking.end_time) for booking in bookings):
                    continue
                if start_utc not in merged:
                    merged[start_utc] = (end_utc, set())
                merged[start_utc][1].add(staff_member.id)

    return [
        AvailableSlot(start_time=start_time, end_time=end_time, available_staff=tuple(sorted(staff_ids)))
        for start_time, (end_time, staff_ids) in sorted(merged.items(), key=lambda item: item[0])
    ]


async def load_tenant(db: AsyncSession, tenant_id: UUID) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.status == "active"))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "TENANT_NOT_FOUND", "message": "Tenant was not found."})
    return tenant


async def load_service(db: AsyncSession, tenant_id: UUID, service_id: UUID) -> Service:
    result = await db.execute(select(Service).where(Service.tenant_id == tenant_id, Service.id == service_id, Service.is_active.is_(True)))
    service = result.scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "SERVICE_NOT_FOUND", "message": "Service was not found."})
    return service


async def load_candidate_staff(db: AsyncSession, *, tenant_id: UUID, service_id: UUID, staff_id: UUID | None) -> list[Staff]:
    stmt = (
        select(Staff)
        .join(staff_services, staff_services.c.staff_id == Staff.id)
        .where(
            Staff.tenant_id == tenant_id,
            Staff.is_active.is_(True),
            Staff.is_bookable.is_(True),
            staff_services.c.service_id == service_id,
        )
        .order_by(Staff.name)
    )
    if staff_id is not None:
        stmt = stmt.where(Staff.id == staff_id)
    result = await db.execute(stmt)
    staff_members = list(result.scalars().all())
    if staff_id is not None and not staff_members:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "STAFF_NOT_AVAILABLE", "message": "Staff member cannot perform this service."},
        )
    return staff_members


async def load_working_windows(db: AsyncSession, tenant_id: UUID, staff_id: UUID, requested_date: date) -> list[LocalWindow]:
    override_result = await db.execute(
        select(AvailabilityOverride).where(
            AvailabilityOverride.tenant_id == tenant_id,
            AvailabilityOverride.date == requested_date,
            or_(AvailabilityOverride.staff_id == staff_id, AvailabilityOverride.staff_id.is_(None)),
        )
    )
    overrides = list(override_result.scalars().all())
    if any(override.is_unavailable for override in overrides):
        return []
    custom_windows = [
        LocalWindow(override.start_time, override.end_time)
        for override in overrides
        if override.start_time is not None and override.end_time is not None
    ]
    if custom_windows:
        return custom_windows

    schedule_result = await db.execute(
        select(AvailabilitySchedule).where(
            AvailabilitySchedule.tenant_id == tenant_id,
            AvailabilitySchedule.day_of_week == requested_date.weekday(),
            AvailabilitySchedule.is_active.is_(True),
            or_(AvailabilitySchedule.staff_id == staff_id, AvailabilitySchedule.staff_id.is_(None)),
        )
    )
    return [LocalWindow(schedule.start_time, schedule.end_time) for schedule in schedule_result.scalars().all()]


async def load_bookings_for_local_date(
    db: AsyncSession,
    tenant_id: UUID,
    staff_id: UUID,
    requested_date: date,
    tenant_zone: ZoneInfo,
) -> list[Booking]:
    local_start = datetime.combine(requested_date, time.min, tenant_zone)
    local_end = local_start + timedelta(days=1)
    result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.staff_id == staff_id,
            Booking.status.in_(("pending_payment", "confirmed")),
            Booking.start_time < local_end.astimezone(UTC),
            Booking.end_time > local_start.astimezone(UTC),
        )
    )
    return list(result.scalars().all())


def validate_requested_date(tenant: Tenant, requested_date: date, now: datetime | None = None) -> None:
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    tenant_today = current_time.astimezone(ZoneInfo(tenant.timezone)).date()
    max_date = tenant_today + timedelta(days=tenant.advance_booking_days)
    if requested_date < tenant_today or requested_date > max_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "DATE_OUT_OF_RANGE", "message": "Date is outside the bookable range."},
        )


def iter_candidate_slots(
    *,
    requested_date: date,
    window: LocalWindow,
    tenant_zone: ZoneInfo,
    duration_minutes: int,
    buffer_minutes: int,
) -> Iterable[tuple[datetime, datetime]]:
    local_start = datetime.combine(requested_date, window.start_time, tenant_zone)
    local_end = datetime.combine(requested_date, window.end_time, tenant_zone)
    slot_start = local_start
    step = timedelta(minutes=duration_minutes + buffer_minutes)
    duration = timedelta(minutes=duration_minutes)
    while slot_start + duration <= local_end:
        slot_end = slot_start + duration
        yield slot_start.astimezone(UTC), slot_end.astimezone(UTC)
        slot_start += step


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    if start_b.tzinfo is None:
        start_b = start_b.replace(tzinfo=UTC)
    if end_b.tzinfo is None:
        end_b = end_b.replace(tzinfo=UTC)
    return start_a < end_b.astimezone(UTC) and end_a > start_b.astimezone(UTC)
