from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.availability import AvailabilityOverride, AvailabilitySchedule
from app.models.staff import Staff
from app.models.user import User
from app.schemas.availability import (
    AvailabilityOverrideCreateRequest,
    AvailabilityOverrideResponse,
    AvailabilityScheduleCreateRequest,
    AvailabilityScheduleResponse,
    AvailabilityScheduleUpdateRequest,
)

router = APIRouter(prefix="/availability", tags=["availability"])


async def validate_staff_belongs_to_tenant(db: AsyncSession, tenant_id: UUID, staff_id: UUID | None) -> None:
    if staff_id is None:
        return
    result = await db.execute(select(Staff.id).where(Staff.tenant_id == tenant_id, Staff.id == staff_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_STAFF", "message": "Staff member does not belong to this tenant."},
        )


@router.get("/schedules", response_model=list[AvailabilityScheduleResponse])
async def list_schedules(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AvailabilitySchedule]:
    result = await db.execute(
        select(AvailabilitySchedule).where(AvailabilitySchedule.tenant_id == current_user.tenant_id).order_by(AvailabilitySchedule.day_of_week)
    )
    return list(result.scalars().all())


@router.post("/schedules", response_model=AvailabilityScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: AvailabilityScheduleCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AvailabilitySchedule:
    await validate_staff_belongs_to_tenant(db, current_user.tenant_id, payload.staff_id)
    schedule = AvailabilitySchedule(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.patch("/schedules/{schedule_id}", response_model=AvailabilityScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    payload: AvailabilityScheduleUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AvailabilitySchedule:
    result = await db.execute(select(AvailabilitySchedule).where(AvailabilitySchedule.tenant_id == current_user.tenant_id, AvailabilitySchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "SCHEDULE_NOT_FOUND", "message": "Schedule was not found."})
    data = payload.model_dump(exclude_unset=True)
    await validate_staff_belongs_to_tenant(db, current_user.tenant_id, data.get("staff_id"))
    start_time = data.get("start_time", schedule.start_time)
    end_time = data.get("end_time", schedule.end_time)
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "VALIDATION_ERROR", "message": "end_time must be after start_time."},
        )
    for field, value in data.items():
        setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(AvailabilitySchedule).where(AvailabilitySchedule.tenant_id == current_user.tenant_id, AvailabilitySchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if schedule is not None:
        await db.delete(schedule)
        await db.commit()


@router.get("/overrides", response_model=list[AvailabilityOverrideResponse])
async def list_overrides(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> list[AvailabilityOverride]:
    result = await db.execute(
        select(AvailabilityOverride).where(
            AvailabilityOverride.tenant_id == current_user.tenant_id,
            AvailabilityOverride.date >= from_date,
            AvailabilityOverride.date <= to_date,
        )
    )
    return list(result.scalars().all())


@router.post("/overrides", response_model=AvailabilityOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_override(
    payload: AvailabilityOverrideCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AvailabilityOverride:
    await validate_staff_belongs_to_tenant(db, current_user.tenant_id, payload.staff_id)
    override = AvailabilityOverride(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(override)
    await db.commit()
    await db.refresh(override)
    return override


@router.delete("/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    override_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(AvailabilityOverride).where(AvailabilityOverride.tenant_id == current_user.tenant_id, AvailabilityOverride.id == override_id))
    override = result.scalar_one_or_none()
    if override is not None:
        await db.delete(override)
        await db.commit()
