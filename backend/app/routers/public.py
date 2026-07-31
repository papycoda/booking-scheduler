import json
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.database import get_db, set_tenant_context
from app.middleware.rate_limiter import limiter
from app.models.booking import Booking, BookingInspoAsset
from app.models.payment import Payment
from app.models.service import Service, staff_services
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.schemas.booking import (
    PublicBookingCancelRequest,
    PublicBookingCreateRequest,
    PublicBookingCreateResponse,
    PublicBookingStatusResponse,
    PublicManagedBookingResponse,
    PublicRescheduleRequestCreate,
    PublicRescheduleRequestResponse,
)
from app.schemas.public import PublicServiceResponse, PublicSlotResponse, PublicStaffResponse, PublicTenantResponse
from app.services.availability_service import generate_available_slots
from app.services.booking_service import create_public_booking
from app.services.booking_management_service import (
    cancel_client_booking,
    get_managed_booking,
    manage_url_for_booking,
    verify_manage_token,
    create_reschedule_request,
)
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
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "VALIDATION_ERROR",
                "message": "Please fix the highlighted booking details.",
                "fields": booking_validation_fields(exc),
            },
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"error": "VALIDATION_ERROR", "message": "Booking details must be valid JSON."},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"error": "VALIDATION_ERROR", "message": str(exc) or "Booking request payload is invalid."},
        ) from exc


def booking_validation_fields(exc: ValidationError) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", [])]
        field = ".".join(loc)
        message = booking_validation_message(field, str(error.get("msg", "Invalid value.")))
        fields.append({"field": field, "message": message})
    return fields


def booking_validation_message(field: str, fallback: str) -> str:
    messages = {
        "client.full_name": "Enter your full name.",
        "client.email": "Enter a valid email address.",
        "client.phone": "Enter a valid phone number with 10 to 15 digits.",
        "client.whatsapp_number": "Enter a valid WhatsApp number with 10 to 15 digits.",
        "service_id": "Choose a valid service.",
        "staff_id": "Choose a valid staff member, or leave staff as any available staff.",
        "start_time": "Choose a valid appointment time.",
    }
    return messages.get(field, fallback)


@router.get("/{slug}/bookings/{booking_id}/status", response_model=PublicBookingStatusResponse)
@limiter.limit("60/minute")
async def public_booking_status(
    request: Request,
    slug: str,
    booking_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Query()] = None,
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
    has_valid_token = bool(token and verify_manage_token(token, booking.manage_token_hash))
    if not has_valid_token:
        return PublicBookingStatusResponse(
            booking_id=booking.id,
            booking_status=booking.status,
            payment_status=payment.status if payment else None,
        )
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
        manage_url=manage_url_for_booking(slug, booking.id, token),
    )


@router.get("/{slug}/bookings/{booking_id}/manage", response_model=PublicManagedBookingResponse)
@limiter.limit("30/minute")
async def public_manage_booking(
    request: Request,
    slug: str,
    booking_id: UUID,
    token: Annotated[str, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicManagedBookingResponse:
    tenant = await get_public_tenant(db, slug)
    return await get_managed_booking(db, tenant=tenant, booking_id=booking_id, token=token)


@router.get("/{slug}/bookings/{booking_id}/reschedule-slots", response_model=list[PublicSlotResponse])
@limiter.limit("30/minute")
async def public_reschedule_slots(
    request: Request,
    slug: str,
    booking_id: UUID,
    token: Annotated[str, Query()],
    requested_date: Annotated[date, Query(alias="date")],
    db: Annotated[AsyncSession, Depends(get_db)],
    staff_id: Annotated[UUID | None, Query()] = None,
) -> list[PublicSlotResponse]:
    tenant = await get_public_tenant(db, slug)
    managed = await get_managed_booking(db, tenant=tenant, booking_id=booking_id, token=token)
    slots = await generate_available_slots(
        db,
        tenant_id=tenant.id,
        service_id=managed.service_id,
        requested_date=requested_date,
        staff_id=staff_id or managed.staff_id,
    )
    return [PublicSlotResponse(start_time=slot.start_time, end_time=slot.end_time) for slot in slots]


@router.post("/{slug}/bookings/{booking_id}/reschedule-requests", response_model=PublicRescheduleRequestResponse)
@limiter.limit("10/minute")
async def public_create_reschedule_request(
    request: Request,
    slug: str,
    booking_id: UUID,
    token: Annotated[str, Query()],
    payload: PublicRescheduleRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicRescheduleRequestResponse:
    tenant = await get_public_tenant(db, slug)
    return await create_reschedule_request(db, tenant=tenant, booking_id=booking_id, token=token, payload=payload)


@router.get("/{slug}/inspo/{stored_filename}")
@limiter.limit("120/minute")
async def public_inspo_asset(
    request: Request,
    slug: str,
    stored_filename: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    tenant = await get_public_tenant(db, slug)
    result = await db.execute(
        select(BookingInspoAsset).where(
            BookingInspoAsset.tenant_id == tenant.id,
            BookingInspoAsset.stored_filename == stored_filename,
        )
    )
    asset = result.scalar_one_or_none()
    if asset is None or asset.data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "INSPO_NOT_FOUND", "message": "Inspiration image was not found."})
    return Response(content=asset.data, media_type=asset.content_type, headers={"X-Content-Type-Options": "nosniff"})


@router.post("/{slug}/bookings/{booking_id}/cancel", status_code=204)
@limiter.limit("10/minute")
async def public_cancel_booking(
    request: Request,
    slug: str,
    booking_id: UUID,
    token: Annotated[str, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: PublicBookingCancelRequest | None = None,
) -> None:
    tenant = await get_public_tenant(db, slug)
    await cancel_client_booking(db, tenant=tenant, booking_id=booking_id, token=token, reason=payload.reason if payload else None)
