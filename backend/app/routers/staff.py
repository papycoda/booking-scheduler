from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.service import Service, staff_services
from app.models.staff import Staff
from app.models.user import User
from app.schemas.staff import StaffCreateRequest, StaffResponse, StaffServiceAssignmentRequest, StaffUpdateRequest

router = APIRouter(prefix="/staff", tags=["staff"])


async def get_tenant_staff(db: AsyncSession, tenant_id: UUID, staff_id: UUID) -> Staff:
    result = await db.execute(select(Staff).where(Staff.tenant_id == tenant_id, Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "STAFF_NOT_FOUND", "message": "Staff member was not found."},
        )
    return staff


@router.get("", response_model=list[StaffResponse])
async def list_staff(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Staff]:
    result = await db.execute(select(Staff).where(Staff.tenant_id == current_user.tenant_id).order_by(Staff.name))
    return list(result.scalars().all())


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Staff:
    staff = Staff(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


@router.get("/{staff_id}", response_model=StaffResponse)
async def read_staff(
    staff_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Staff:
    return await get_tenant_staff(db, current_user.tenant_id, staff_id)


@router.patch("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: UUID,
    payload: StaffUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Staff:
    staff = await get_tenant_staff(db, current_user.tenant_id, staff_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)
    await db.commit()
    await db.refresh(staff)
    return staff


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(
    staff_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    staff = await get_tenant_staff(db, current_user.tenant_id, staff_id)
    staff.is_active = False
    await db.commit()


@router.post("/{staff_id}/services", status_code=status.HTTP_204_NO_CONTENT)
async def assign_staff_services(
    staff_id: UUID,
    payload: StaffServiceAssignmentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await get_tenant_staff(db, current_user.tenant_id, staff_id)
    if payload.service_ids:
        result = await db.execute(select(Service.id).where(Service.tenant_id == current_user.tenant_id, Service.id.in_(payload.service_ids)))
        found_service_ids = set(result.scalars().all())
        if found_service_ids != set(payload.service_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_SERVICE_ASSIGNMENT", "message": "One or more services do not belong to this tenant."},
            )

    await db.execute(delete(staff_services).where(staff_services.c.staff_id == staff_id))
    if payload.service_ids:
        await db.execute(insert(staff_services), [{"staff_id": staff_id, "service_id": service_id} for service_id in payload.service_ids])
    await db.commit()


@router.delete("/{staff_id}/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_staff_service(
    staff_id: UUID,
    service_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await get_tenant_staff(db, current_user.tenant_id, staff_id)
    await db.execute(delete(staff_services).where(staff_services.c.staff_id == staff_id, staff_services.c.service_id == service_id))
    await db.commit()
