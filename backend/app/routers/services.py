from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreateRequest, ServiceResponse, ServiceUpdateRequest

router = APIRouter(prefix="/services", tags=["services"])


async def get_tenant_service(db: AsyncSession, tenant_id: UUID, service_id: UUID) -> Service:
    result = await db.execute(select(Service).where(Service.tenant_id == tenant_id, Service.id == service_id))
    service = result.scalar_one_or_none()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SERVICE_NOT_FOUND", "message": "Service was not found."},
        )
    return service


@router.get("", response_model=list[ServiceResponse])
async def list_services(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Service]:
    result = await db.execute(
        select(Service).where(Service.tenant_id == current_user.tenant_id, Service.is_active.is_(True)).order_by(Service.name)
    )
    return list(result.scalars().all())


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Service:
    service = Service(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    payload: ServiceUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Service:
    service = await get_tenant_service(db, current_user.tenant_id, service_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = await get_tenant_service(db, current_user.tenant_id, service_id)
    service.is_active = False
    await db.commit()
