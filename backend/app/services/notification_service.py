import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.booking import Booking, BookingRescheduleRequest, Client
from app.models.notification import NotificationLog
from app.models.service import Service
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.models.user import User
from app.services.booking_management_service import create_manage_token_for_booking, manage_url_for_booking

logger = logging.getLogger(__name__)


async def send_email(
    *,
    to_email: str,
    subject: str,
    text: str,
    html: str | None = None,
    idempotency_key: str | None = None,
) -> bool:
    if not settings.resend_api_key or not settings.from_email:
        logger.info("Skipping email notification because Resend is not configured")
        return False
    payload = {
        "from": settings.from_email,
        "to": [to_email],
        "subject": subject,
        "text": text,
        "html": html or f"<p>{text}</p>",
    }
    headers = {"Authorization": f"Bearer {settings.resend_api_key}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
    response.raise_for_status()
    return True


async def send_password_reset_email(*, to_email: str, reset_url: str) -> None:
    await send_email(
        to_email=to_email,
        subject="Reset your booking scheduler password",
        text=f"Use this link to reset your password: {reset_url}. This link expires in 1 hour.",
        html=f"<p>Use this link to reset your password:</p><p><a href=\"{reset_url}\">{reset_url}</a></p><p>This link expires in 1 hour.</p>",
    )


async def send_whatsapp_template(*, to_number: str, template_name: str, body_params: list[str]) -> bool:
    body = format_whatsapp_body(template_name, body_params)
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_from_number:
        logger.info("Skipping WhatsApp notification because Twilio is not configured")
        return False
    payload = {
        "From": f"whatsapp:{settings.twilio_whatsapp_from_number}",
        "To": f"whatsapp:{to_number}",
        "Body": body,
    }
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, data=payload, auth=(settings.twilio_account_sid, settings.twilio_auth_token))
    response.raise_for_status()
    return True


def format_whatsapp_body(template_name: str, body_params: list[str]) -> str:
    if template_name == "booking_confirmation" and len(body_params) >= 5:
        full_name, service_name, staff_name, start_time, booking_id = body_params[:5]
        return (
            f"Hi {full_name}, your {service_name} appointment with {staff_name} is confirmed for {start_time}. "
            f"Reference: {booking_id}. Deposits are non-refundable."
        )
    if template_name == "booking_reminder" and len(body_params) >= 3:
        service_name, start_time, staff_name = body_params[:3]
        return f"Reminder: Your {service_name} appointment is at {start_time} with {staff_name}."
    return " ".join(body_params).strip()


async def notification_already_sent(
    db: AsyncSession,
    booking_id,
    recipient_type: str,
    channel: str,
    notification_type: str,
) -> bool:
    result = await db.execute(
        select(NotificationLog.id).where(
            NotificationLog.booking_id == booking_id,
            NotificationLog.recipient_type == recipient_type,
            NotificationLog.channel == channel,
            NotificationLog.type == notification_type,
            NotificationLog.status == "sent",
        )
    )
    return result.scalar_one_or_none() is not None


async def log_notification(
    db: AsyncSession,
    *,
    tenant_id,
    booking_id,
    recipient_type: str,
    channel: str,
    notification_type: str,
    status: str,
    error_message: str | None = None,
) -> None:
    db.add(
        NotificationLog(
            tenant_id=tenant_id,
            booking_id=booking_id,
            recipient_type=recipient_type,
            channel=channel,
            type=notification_type,
            status=status,
            error_message=error_message,
            sent_at=datetime.now(UTC) if status == "sent" else None,
        )
    )
    await db.commit()


async def send_booking_confirmation(db: AsyncSession, booking: Booking) -> None:
    context = await load_booking_context(db, booking)
    tenant, client, service, staff = context
    manage_url = manage_url_for_booking(tenant.slug, booking.id, create_manage_token_for_booking(booking.id))
    manage_text = f" Manage your booking here: {manage_url}. Deposits are non-refundable." if manage_url else " Deposits are non-refundable."
    text = (
        f"Hi {client.full_name}, your {service.name} appointment with {staff.name} "
        f"is confirmed for {booking.start_time.isoformat()}. Ref: {booking.id}.{manage_text}"
    )
    await send_and_log_email(
        db,
        booking=booking,
        recipient_type="client",
        notification_type="booking_confirmation",
        to_email=client.email,
        subject=f"{tenant.name} booking confirmation",
        text=text,
    )
    if client.whatsapp_number:
        await send_and_log_whatsapp(
            db,
            booking=booking,
            recipient_type="client",
            notification_type="booking_confirmation",
            to_number=client.whatsapp_number,
            template_name="booking_confirmation",
            body_params=[client.full_name, service.name, staff.name, booking.start_time.isoformat(), str(booking.id)],
        )
    owner = await load_tenant_owner(db, tenant.id)
    if owner is not None:
        await send_and_log_email(
            db,
            booking=booking,
            recipient_type="owner",
            notification_type="booking_confirmation",
            to_email=owner.email,
            subject=f"New booking for {tenant.name}",
            text=(
                f"New booking: {client.full_name} booked {service.name} with {staff.name} "
                f"for {booking.start_time.isoformat()}."
            ),
        )


async def send_reschedule_request_notification(db: AsyncSession, request_id) -> None:
    context = await load_reschedule_context(db, request_id)
    if context is None:
        return
    request, booking, tenant, client, service, current_staff, requested_staff = context
    owner = await load_tenant_owner(db, tenant.id)
    if owner is None:
        return
    await send_email(
        to_email=owner.email,
        subject=f"Reschedule request for {tenant.name}",
        text=(
            f"{client.full_name} requested to move {service.name} from {booking.start_time.isoformat()} "
            f"with {current_staff.name} to {request.requested_start_time.isoformat()} with {requested_staff.name}. "
            f"The requested slot is held until {request.hold_expires_at.isoformat()}."
        ),
    )


async def send_reschedule_decision_notification(db: AsyncSession, request_id) -> None:
    context = await load_reschedule_context(db, request_id)
    if context is None:
        return
    request, _booking, tenant, client, service, _current_staff, requested_staff = context
    decision_text = "approved" if request.status == "approved" else "rejected"
    await send_email(
        to_email=client.email,
        subject=f"{tenant.name} reschedule request {decision_text}",
        text=(
            f"Your reschedule request for {service.name} was {decision_text}. "
            f"Requested time: {request.requested_start_time.isoformat()} with {requested_staff.name}. "
            "Deposits are non-refundable."
        ),
    )


async def send_booking_reminder(db: AsyncSession, booking: Booking, reminder_type: str) -> bool:
    tenant, client, service, staff = await load_booking_context(db, booking)
    text = f"Reminder: Your {service.name} appointment is at {booking.start_time.isoformat()} with {staff.name}."
    sent_email = await send_and_log_email(
        db,
        booking=booking,
        recipient_type="client",
        notification_type=reminder_type,
        to_email=client.email,
        subject=f"{tenant.name} appointment reminder",
        text=text,
    )
    sent_whatsapp = False
    if client.whatsapp_number:
        sent_whatsapp = await send_and_log_whatsapp(
            db,
            booking=booking,
            recipient_type="client",
            notification_type=reminder_type,
            to_number=client.whatsapp_number,
            template_name="booking_reminder",
            body_params=[service.name, booking.start_time.isoformat(), staff.name],
        )
    return sent_email or sent_whatsapp


async def send_and_log_email(
    db: AsyncSession,
    *,
    booking: Booking,
    recipient_type: str,
    notification_type: str,
    to_email: str,
    subject: str,
    text: str,
) -> bool:
    if await notification_already_sent(db, booking.id, recipient_type, "email", notification_type):
        return False
    try:
        sent = await send_email(
            to_email=to_email,
            subject=subject,
            text=text,
            idempotency_key=f"notification:{booking.id}:{recipient_type}:email:{notification_type}",
        )
        if not sent:
            await log_notification(
                db,
                tenant_id=booking.tenant_id,
                booking_id=booking.id,
                recipient_type=recipient_type,
                channel="email",
                notification_type=notification_type,
                status="failed",
                error_message="Email provider is not configured",
            )
            return False
        await log_notification(
            db,
            tenant_id=booking.tenant_id,
            booking_id=booking.id,
            recipient_type=recipient_type,
            channel="email",
            notification_type=notification_type,
            status="sent",
        )
        return True
    except Exception as exc:
        logger.exception("Email notification failed")
        await log_notification(
            db,
            tenant_id=booking.tenant_id,
            booking_id=booking.id,
            recipient_type=recipient_type,
            channel="email",
            notification_type=notification_type,
            status="failed",
            error_message=str(exc),
        )
        return False


async def send_and_log_whatsapp(
    db: AsyncSession,
    *,
    booking: Booking,
    recipient_type: str,
    notification_type: str,
    to_number: str,
    template_name: str,
    body_params: list[str],
) -> bool:
    if await notification_already_sent(db, booking.id, recipient_type, "whatsapp", notification_type):
        return False
    try:
        sent = await send_whatsapp_template(to_number=to_number, template_name=template_name, body_params=body_params)
        if not sent:
            await log_notification(
                db,
                tenant_id=booking.tenant_id,
                booking_id=booking.id,
                recipient_type=recipient_type,
                channel="whatsapp",
                notification_type=notification_type,
                status="failed",
                error_message="WhatsApp provider is not configured",
            )
            return False
        await log_notification(
            db,
            tenant_id=booking.tenant_id,
            booking_id=booking.id,
            recipient_type=recipient_type,
            channel="whatsapp",
            notification_type=notification_type,
            status="sent",
        )
        return True
    except Exception as exc:
        logger.exception("WhatsApp notification failed")
        await log_notification(
            db,
            tenant_id=booking.tenant_id,
            booking_id=booking.id,
            recipient_type=recipient_type,
            channel="whatsapp",
            notification_type=notification_type,
            status="failed",
            error_message=str(exc),
        )
        return False


async def load_booking_context(db: AsyncSession, booking: Booking) -> tuple[Tenant, Client, Service, Staff]:
    result = await db.execute(
        select(Tenant, Client, Service, Staff)
        .select_from(Tenant)
        .join(Client, Client.tenant_id == Tenant.id)
        .join(Service, Service.tenant_id == Tenant.id)
        .join(Staff, Staff.tenant_id == Tenant.id)
        .where(
            Tenant.id == booking.tenant_id,
            Client.id == booking.client_id,
            Service.id == booking.service_id,
            Staff.id == booking.staff_id,
        )
    )
    return result.one()


async def load_reschedule_context(db: AsyncSession, request_id):
    from sqlalchemy.orm import aliased

    current_staff = aliased(Staff)
    requested_staff = aliased(Staff)
    result = await db.execute(
        select(BookingRescheduleRequest, Booking, Tenant, Client, Service, current_staff, requested_staff)
        .join(Booking, Booking.id == BookingRescheduleRequest.booking_id)
        .join(Tenant, Tenant.id == BookingRescheduleRequest.tenant_id)
        .join(Client, Client.id == Booking.client_id)
        .join(Service, Service.id == Booking.service_id)
        .join(current_staff, current_staff.id == Booking.staff_id)
        .join(requested_staff, requested_staff.id == BookingRescheduleRequest.requested_staff_id)
        .where(BookingRescheduleRequest.id == request_id)
    )
    return result.one_or_none()


async def load_tenant_owner(db: AsyncSession, tenant_id) -> User | None:
    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.role == "tenant_owner",
            User.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def send_whatsapp_message(*, to_number: str, body: str) -> str | None:
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_from_number:
        logger.info("Skipping WhatsApp notification because Twilio is not configured")
        return None
    payload = {
        "From": f"whatsapp:{settings.twilio_whatsapp_from_number}",
        "To": f"whatsapp:{to_number}",
        "Body": body,
    }
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, data=payload, auth=(settings.twilio_account_sid, settings.twilio_auth_token))
    response.raise_for_status()
    try:
        return response.json().get("sid")
    except Exception:
        return None


async def process_due_reminders(db: AsyncSession) -> int:
    now = datetime.now(UTC)
    windows = [
        ("booking_reminder_24h", now + timedelta(hours=23), now + timedelta(hours=25)),
        ("booking_reminder_1h", now + timedelta(minutes=55), now + timedelta(minutes=65)),
    ]
    sent_count = 0
    for reminder_type, start_time, end_time in windows:
        result = await db.execute(
            select(Booking).where(
                Booking.status == "confirmed",
                Booking.start_time >= start_time,
                Booking.start_time <= end_time,
            )
        )
        for booking in result.scalars().all():
            if await send_booking_reminder(db, booking, reminder_type):
                sent_count += 1
    return sent_count
