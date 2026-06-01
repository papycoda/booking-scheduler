import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.booking import Booking, BookingRescheduleRequest, Client
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.booking import PublicManagedBookingResponse, PublicRescheduleRequestCreate, PublicRescheduleRequestResponse, PublicRescheduleRequestSummary
from app.schemas.dashboard import DashboardRescheduleRequestResponse
from app.services.availability_service import generate_available_slots

RESCHEDULE_HOLD_HOURS = 24
logger = logging.getLogger(__name__)


def create_manage_token_pair() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_manage_token(raw_token)


def create_manage_token_for_booking(booking_id: UUID) -> str:
    digest = hmac.new(secret_key_bytes(), f"manage:{booking_id}".encode(), hashlib.sha256).hexdigest()
    return digest


def hash_manage_token(raw_token: str) -> str:
    return hmac.new(secret_key_bytes(), raw_token.encode(), hashlib.sha256).hexdigest()


def secret_key_bytes() -> bytes:
    secret = settings.secret_key
    if hasattr(secret, "get_secret_value"):
        secret = secret.get_secret_value()
    return str(secret).encode()


def verify_manage_token(raw_token: str, token_hash: str | None) -> bool:
    if not raw_token or not token_hash:
        return False
    return hmac.compare_digest(hash_manage_token(raw_token), token_hash)


def manage_url_for_booking(slug: str, booking_id: UUID, token: str) -> str:
    return f"{str(settings.frontend_url).rstrip('/')}/book/{slug}/manage/{booking_id}?token={token}"


async def get_managed_booking(
    db: AsyncSession,
    *,
    tenant: Tenant,
    booking_id: UUID,
    token: str,
) -> PublicManagedBookingResponse:
    row = await load_managed_booking_row(db, tenant_id=tenant.id, booking_id=booking_id, token=token)
    booking, _client, service, staff, payment = row
    pending_requests = await load_public_reschedule_requests(db, tenant.id, booking.id)
    cancellation_deadline = booking.start_time - timedelta(hours=tenant.cancellation_notice_hours)
    now = datetime.now(UTC)
    return PublicManagedBookingResponse(
        booking_id=booking.id,
        booking_status=booking.status,
        payment_status=payment.status if payment else None,
        start_time=booking.start_time,
        end_time=booking.end_time,
        service_id=service.id,
        service_name=service.name,
        staff_id=staff.id,
        staff_name=staff.name,
        deposit_amount=booking.deposit_amount,
        price_status=booking.price_status,
        quoted_price=booking.quoted_price,
        cancellation_deadline=cancellation_deadline,
        can_cancel=booking.status in ("pending_payment", "confirmed") and now <= cancellation_deadline,
        pending_reschedule_requests=pending_requests,
    )


async def cancel_client_booking(
    db: AsyncSession,
    *,
    tenant: Tenant,
    booking_id: UUID,
    token: str,
    reason: str | None = None,
) -> None:
    result = await db.execute(select(Booking).where(Booking.tenant_id == tenant.id, Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None or not verify_manage_token(token, booking.manage_token_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    cancellation_deadline = booking.start_time - timedelta(hours=tenant.cancellation_notice_hours)
    if datetime.now(UTC) > cancellation_deadline:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CANCELLATION_WINDOW_CLOSED", "message": "This booking can no longer be cancelled online."},
        )
    booking.status = "cancelled"
    booking.cancelled_by = "client"
    booking.cancelled_at = datetime.now(UTC)
    booking.cancellation_reason = reason
    await cancel_pending_reschedule_requests(db, tenant.id, booking.id)
    await db.commit()


async def create_reschedule_request(
    db: AsyncSession,
    *,
    tenant: Tenant,
    booking_id: UUID,
    token: str,
    payload: PublicRescheduleRequestCreate,
) -> PublicRescheduleRequestResponse:
    result = await db.execute(select(Booking).where(Booking.tenant_id == tenant.id, Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None or not verify_manage_token(token, booking.manage_token_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    if booking.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "BOOKING_NOT_CONFIRMED", "message": "Only confirmed bookings can be rescheduled online."},
        )
    active_result = await db.execute(
        select(BookingRescheduleRequest.id).where(
            BookingRescheduleRequest.tenant_id == tenant.id,
            BookingRescheduleRequest.booking_id == booking.id,
            BookingRescheduleRequest.status == "pending",
            BookingRescheduleRequest.hold_expires_at > datetime.now(UTC),
        )
    )
    if active_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "ACTIVE_RESCHEDULE_REQUEST", "message": "This booking already has a pending reschedule request."},
        )

    start_utc = payload.start_time.astimezone(UTC)
    requested_date = payload.start_time.astimezone(__import__("zoneinfo").ZoneInfo(tenant.timezone)).date()
    staff_id = payload.staff_id or booking.staff_id
    slots = await generate_available_slots(
        db,
        tenant_id=tenant.id,
        service_id=booking.service_id,
        requested_date=requested_date,
        staff_id=staff_id,
    )
    matching_slot = next((slot for slot in slots if slot.start_time == start_utc and staff_id in slot.available_staff), None)
    if matching_slot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "SLOT_UNAVAILABLE", "message": "This slot is no longer available."},
        )
    request = BookingRescheduleRequest(
        tenant_id=tenant.id,
        booking_id=booking.id,
        requested_staff_id=staff_id,
        requested_start_time=start_utc,
        requested_end_time=matching_slot.end_time,
        status="pending",
        hold_expires_at=datetime.now(UTC) + timedelta(hours=RESCHEDULE_HOLD_HOURS),
        client_note=payload.note,
    )
    db.add(request)
    await db.flush()
    await db.commit()
    from app.services.notification_service import send_reschedule_request_notification

    try:
        await send_reschedule_request_notification(db, request.id)
    except Exception:
        logger.info("Reschedule request notification failed")
    return reschedule_request_to_public_response(request)


async def decide_reschedule_request(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    request_id: UUID,
    user_id: UUID,
    decision: str,
    note: str | None = None,
) -> None:
    result = await db.execute(
        select(BookingRescheduleRequest, Booking)
        .join(Booking, Booking.id == BookingRescheduleRequest.booking_id)
        .where(BookingRescheduleRequest.tenant_id == tenant_id, BookingRescheduleRequest.id == request_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "RESCHEDULE_REQUEST_NOT_FOUND", "message": "Request was not found."})
    request, booking = row
    if request.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "REQUEST_NOT_PENDING", "message": "Request is no longer pending."})
    if decision == "approved":
        if datetime.now(UTC) > request.hold_expires_at:
            request.status = "expired"
            await db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "HOLD_EXPIRED", "message": "This requested slot hold has expired."})
        await ensure_reschedule_approval_slot_available(db, tenant_id=tenant_id, request=request, booking=booking)
        booking.staff_id = request.requested_staff_id
        booking.start_time = request.requested_start_time
        booking.end_time = request.requested_end_time
        request.status = "approved"
    else:
        request.status = "rejected"
    request.decision_note = note
    request.decided_at = datetime.now(UTC)
    request.decided_by_user_id = user_id
    await db.commit()
    from app.services.notification_service import send_reschedule_decision_notification

    try:
        await send_reschedule_decision_notification(db, request.id)
    except Exception:
        logger.info("Reschedule decision notification failed")


async def ensure_reschedule_approval_slot_available(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    request: BookingRescheduleRequest,
    booking: Booking,
) -> None:
    booking_conflict_result = await db.execute(
        select(Booking.id).where(
            Booking.tenant_id == tenant_id,
            Booking.staff_id == request.requested_staff_id,
            Booking.id != booking.id,
            Booking.status.in_(("pending_payment", "confirmed")),
            Booking.start_time < request.requested_end_time,
            Booking.end_time > request.requested_start_time,
        )
    )
    if booking_conflict_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "SLOT_UNAVAILABLE", "message": "Requested slot is no longer available."})
    hold_conflict_result = await db.execute(
        select(BookingRescheduleRequest.id).where(
            BookingRescheduleRequest.tenant_id == tenant_id,
            BookingRescheduleRequest.requested_staff_id == request.requested_staff_id,
            BookingRescheduleRequest.id != request.id,
            BookingRescheduleRequest.status == "pending",
            BookingRescheduleRequest.hold_expires_at > datetime.now(UTC),
            BookingRescheduleRequest.requested_start_time < request.requested_end_time,
            BookingRescheduleRequest.requested_end_time > request.requested_start_time,
        )
    )
    if hold_conflict_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "SLOT_UNAVAILABLE", "message": "Requested slot is no longer available."})


async def load_managed_booking_row(db: AsyncSession, *, tenant_id: UUID, booking_id: UUID, token: str):
    result = await db.execute(
        select(Booking, Client, Service, Staff, Payment)
        .join(Client, Client.id == Booking.client_id)
        .join(Service, Service.id == Booking.service_id)
        .join(Staff, Staff.id == Booking.staff_id)
        .join(Payment, Payment.booking_id == Booking.id, isouter=True)
        .where(Booking.tenant_id == tenant_id, Booking.id == booking_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    if not verify_manage_token(token, row[0].manage_token_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    return row


async def load_public_reschedule_requests(db: AsyncSession, tenant_id: UUID, booking_id: UUID) -> list[PublicRescheduleRequestSummary]:
    result = await db.execute(
        select(BookingRescheduleRequest, Staff)
        .join(Staff, Staff.id == BookingRescheduleRequest.requested_staff_id)
        .where(BookingRescheduleRequest.tenant_id == tenant_id, BookingRescheduleRequest.booking_id == booking_id)
        .order_by(BookingRescheduleRequest.created_at.desc())
    )
    return [
        PublicRescheduleRequestSummary(
            id=request.id,
            status=request.status,
            requested_start_time=request.requested_start_time,
            requested_end_time=request.requested_end_time,
            requested_staff_id=request.requested_staff_id,
            staff_name=staff.name,
            hold_expires_at=request.hold_expires_at,
            client_note=request.client_note,
            decision_note=request.decision_note,
        )
        for request, staff in result.all()
    ]


async def cancel_pending_reschedule_requests(db: AsyncSession, tenant_id: UUID, booking_id: UUID) -> None:
    result = await db.execute(
        select(BookingRescheduleRequest).where(
            BookingRescheduleRequest.tenant_id == tenant_id,
            BookingRescheduleRequest.booking_id == booking_id,
            BookingRescheduleRequest.status == "pending",
        )
    )
    for request in result.scalars().all():
        request.status = "cancelled"
    await db.commit()


def reschedule_request_to_public_response(request: BookingRescheduleRequest) -> PublicRescheduleRequestResponse:
    return PublicRescheduleRequestResponse(
        id=request.id,
        status=request.status,
        requested_start_time=request.requested_start_time,
        requested_end_time=request.requested_end_time,
        requested_staff_id=request.requested_staff_id,
        hold_expires_at=request.hold_expires_at,
        client_note=request.client_note,
    )


def dashboard_reschedule_row_to_response(row) -> DashboardRescheduleRequestResponse:
    request, booking, client, service, current_staff, requested_staff = row
    return DashboardRescheduleRequestResponse(
        id=request.id,
        booking_id=booking.id,
        status=request.status,
        client_name=client.full_name,
        client_email=client.email,
        service_name=service.name,
        current_staff_name=current_staff.name,
        requested_staff_name=requested_staff.name,
        current_start_time=booking.start_time,
        current_end_time=booking.end_time,
        requested_start_time=request.requested_start_time,
        requested_end_time=request.requested_end_time,
        hold_expires_at=request.hold_expires_at,
        client_note=request.client_note,
        decision_note=request.decision_note,
    )
