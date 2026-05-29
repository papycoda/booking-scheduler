import json
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.database import get_db, set_tenant_context
from app.middleware.rate_limiter import limiter
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.service import Service, staff_services
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.schemas.booking import PublicBookingCreateRequest, PublicBookingCreateResponse, PublicBookingStatusResponse
from app.schemas.public import PublicServiceResponse, PublicSlotResponse, PublicStaffResponse, PublicTenantResponse
from app.services.availability_service import generate_available_slots
from app.services.booking_service import create_public_booking
from app.services.pricing_service import calculate_deposit_due_now, price_label_for_service

router = APIRouter(prefix="/book", tags=["public booking"])


async def get_public_tenant(db: AsyncSession, slug: str) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug, Tenant.status == "active"))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "TENANT_NOT_FOUND", "message": "Booking page was not found."})
    await set_tenant_context(db, tenant.id)
    return tenant


@router.get("/{slug}", response_model=PublicTenantResponse)
@limiter.limit("60/minute")
async def public_tenant(request: Request, slug: str, db: Annotated[AsyncSession, Depends(get_db)]) -> PublicTenantResponse:
    tenant = await get_public_tenant(db, slug)
    return PublicTenantResponse(
        slug=tenant.slug,
        name=tenant.name,
        description=tenant.description,
        logo_url=tenant.logo_url,
        timezone=tenant.timezone,
        allow_staff_selection=tenant.allow_staff_selection,
        advance_booking_days=tenant.advance_booking_days,
    )


@router.get("/{slug}/services", response_model=list[PublicServiceResponse])
@limiter.limit("60/minute")
async def public_services(request: Request, slug: str, db: Annotated[AsyncSession, Depends(get_db)]) -> list[PublicServiceResponse]:
    tenant = await get_public_tenant(db, slug)
    result = await db.execute(select(Service).where(Service.tenant_id == tenant.id, Service.is_active.is_(True)).order_by(Service.name))
    return [
        PublicServiceResponse(
            id=service.id,
            name=service.name,
            description=service.description,
            duration_minutes=service.duration_minutes,
            price=service.price,
            currency=service.currency,
            pricing_mode=service.pricing_mode,
            deposit_policy=service.deposit_policy,
            deposit_amount=service.deposit_amount,
            is_active=service.is_active,
            deposit_due_now=calculate_deposit_due_now(tenant, service),
            price_label=price_label_for_service(service),
        )
        for service in result.scalars().all()
    ]


@router.get("/{slug}/staff", response_model=list[PublicStaffResponse])
@limiter.limit("60/minute")
async def public_staff(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    service_id: UUID | None = None,
) -> list[Staff]:
    tenant = await get_public_tenant(db, slug)
    stmt = select(Staff).where(Staff.tenant_id == tenant.id, Staff.is_active.is_(True), Staff.is_bookable.is_(True)).order_by(Staff.name)
    if service_id is not None:
        service_result = await db.execute(
            select(Service.id).where(Service.tenant_id == tenant.id, Service.id == service_id, Service.is_active.is_(True))
        )
        if service_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "SERVICE_NOT_FOUND", "message": "Service was not found."},
            )
        stmt = stmt.join(staff_services, staff_services.c.staff_id == Staff.id).where(staff_services.c.service_id == service_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{slug}/slots", response_model=list[PublicSlotResponse])
@limiter.limit("30/minute")
async def public_slots(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    service_id: Annotated[UUID, Query()],
    requested_date: Annotated[date, Query(alias="date")],
    staff_id: Annotated[UUID | None, Query()] = None,
) -> list[PublicSlotResponse]:
    tenant = await get_public_tenant(db, slug)
    slots = await generate_available_slots(db, tenant_id=tenant.id, service_id=service_id, requested_date=requested_date, staff_id=staff_id)
    return [PublicSlotResponse(start_time=slot.start_time, end_time=slot.end_time) for slot in slots]


@router.post("/{slug}/bookings", response_model=PublicBookingCreateResponse)
@limiter.limit("10/minute")
async def public_create_booking(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicBookingCreateResponse:
    tenant = await get_public_tenant(db, slug)
    payload, inspo_images = await parse_public_booking_request(request)
    return await create_public_booking(db, tenant=tenant, slug=slug, payload=payload, inspo_images=inspo_images)


async def parse_public_booking_request(request: Request) -> tuple[PublicBookingCreateRequest, list[UploadFile]]:
    content_type = request.headers.get("content-type", "")
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            raw_payload = form.get("payload")
            if not isinstance(raw_payload, str):
                raise ValueError("payload is required")
            files = [item for item in form.getlist("inspo_images") if isinstance(item, StarletteUploadFile)]
            return PublicBookingCreateRequest.model_validate(json.loads(raw_payload)), files
        return PublicBookingCreateRequest.model_validate(await request.json()), []
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "VALIDATION_ERROR", "message": "Booking request payload is invalid."},
        ) from exc


@router.get("/{slug}/bookings/{booking_id}/status", response_model=PublicBookingStatusResponse)
@limiter.limit("60/minute")
async def public_booking_status(
    request: Request,
    slug: str,
    booking_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicBookingStatusResponse:
    tenant = await get_public_tenant(db, slug)
    result = await db.execute(
        select(Booking, Payment, Service, Staff)
        .join(Payment, Payment.booking_id == Booking.id, isouter=True)
        .join(Service, Service.id == Booking.service_id)
        .join(Staff, Staff.id == Booking.staff_id)
        .where(Booking.tenant_id == tenant.id, Booking.id == booking_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    booking, payment, service, staff = row
    return PublicBookingStatusResponse(
        booking_id=booking.id,
        booking_status=booking.status,
        payment_status=payment.status if payment else None,
        reference=payment.paystack_reference if payment else None,
        start_time=booking.start_time,
        end_time=booking.end_time,
        service_name=service.name,
        staff_name=staff.name,
        deposit_amount=booking.deposit_amount,
        price_status=booking.price_status,
        quoted_price=booking.quoted_price,
    )


@router.post("/{slug}/bookings/{booking_id}/cancel", status_code=204)
@limiter.limit("10/minute")
async def public_cancel_booking(
    request: Request,
    slug: str,
    booking_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    tenant = await get_public_tenant(db, slug)
    result = await db.execute(select(Booking).where(Booking.tenant_id == tenant.id, Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        return
    cancellation_deadline = booking.start_time - timedelta(hours=tenant.cancellation_notice_hours)
    if datetime.now(UTC) > cancellation_deadline:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CANCELLATION_WINDOW_CLOSED", "message": "This booking can no longer be cancelled online."},
        )
    booking.status = "cancelled"
    booking.cancelled_by = "client"
    booking.cancelled_at = datetime.now(UTC)
    await db.commit()
