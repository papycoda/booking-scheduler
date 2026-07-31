import logging
from datetime import UTC, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

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


def format_local_datetime(value: datetime, timezone: str) -> str:
    local_value = value.astimezone(ZoneInfo(timezone))
    time_label = local_value.strftime("%I:%M %p").lstrip("0")
    return f"{local_value.strftime('%A')}, {local_value.day} {local_value.strftime('%B %Y')} at {time_label}"


def build_booking_confirmation_content(
    *,
    client_name: str,
    tenant_name: str,
    service_name: str,
    staff_name: str,
    start_time: datetime,
    timezone: str,
    manage_url: str | None,
) -> tuple[str, str]:
    time_label = format_local_datetime(start_time, timezone)
    text_lines = [
        f"Hi {client_name},",
        "",
        f"Your booking with {tenant_name} is confirmed.",
        "",
        f"Service: {service_name}",
        f"With: {staff_name}",
        f"When: {time_label}",
    ]
    if manage_url:
        text_lines.extend(
            [
                "",
                f"Manage your booking: {manage_url}",
                "",
                "If the link does not open, copy and paste it into your browser.",
            ]
        )
    text_lines.extend(["", "Please note: deposits are non-refundable.", "", f"See you then,", tenant_name])

    safe_client = escape(client_name)
    safe_tenant = escape(tenant_name)
    safe_service = escape(service_name)
    safe_staff = escape(staff_name)
    safe_time = escape(time_label)
    manage_block = ""
    if manage_url:
        safe_url = escape(manage_url, quote=True)
        manage_block = f"""
          <tr><td style="padding:28px 0 0">
            <a href="{safe_url}" style="display:inline-block;background:#0f6b4f;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;padding:14px 22px;border-radius:12px">Manage your booking</a>
          </td></tr>
          <tr><td style="padding:16px 0 0;color:#60766a;font-size:12px;line-height:18px">
            Button not working? Copy and paste this link into your browser:<br>
            <a href="{safe_url}" style="color:#0f6b4f;word-break:break-all">{safe_url}</a>
          </td></tr>
        """

    html = f"""<!doctype html>
<html lang="en">
  <body style="margin:0;background:#f4f8f5;font-family:Arial,Helvetica,sans-serif;color:#0f2119">
    <div style="display:none;max-height:0;overflow:hidden">Your booking with {safe_tenant} is confirmed.</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f8f5;padding:24px 12px">
      <tr><td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border:1px solid #e2ebe5;border-radius:20px;overflow:hidden">
          <tr><td style="background:#0a4d37;padding:24px 30px;color:#ffffff;font-size:25px;font-weight:800;letter-spacing:-1px">Bookie</td></tr>
          <tr><td style="padding:34px 30px">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
              <tr><td><span style="display:inline-block;background:#e8f4ec;color:#0f6b4f;font-size:12px;font-weight:700;padding:7px 11px;border-radius:999px">Booking confirmed</span></td></tr>
              <tr><td style="padding:22px 0 0;font-size:24px;font-weight:800;line-height:31px">You&apos;re booked, {safe_client}.</td></tr>
              <tr><td style="padding:10px 0 0;color:#50685d;font-size:15px;line-height:24px">Your appointment with <strong style="color:#0f2119">{safe_tenant}</strong> is confirmed.</td></tr>
              <tr><td style="padding:24px 0 0">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f9f7;border:1px solid #e2ebe5;border-radius:14px">
                  <tr><td style="padding:18px 20px 8px;color:#60766a;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Appointment details</td></tr>
                  <tr><td style="padding:8px 20px;color:#60766a;font-size:14px">Service<br><strong style="display:block;padding-top:3px;color:#0f2119;font-size:16px">{safe_service}</strong></td></tr>
                  <tr><td style="padding:8px 20px;color:#60766a;font-size:14px">With<br><strong style="display:block;padding-top:3px;color:#0f2119;font-size:16px">{safe_staff}</strong></td></tr>
                  <tr><td style="padding:8px 20px 20px;color:#60766a;font-size:14px">When<br><strong style="display:block;padding-top:3px;color:#0f2119;font-size:16px;line-height:23px">{safe_time}</strong></td></tr>
                </table>
              </td></tr>
              {manage_block}
              <tr><td style="padding:24px 0 0;color:#60766a;font-size:13px;line-height:20px">Please note: deposits are non-refundable.</td></tr>
              <tr><td style="padding:26px 0 0;color:#0f2119;font-size:14px;line-height:22px">See you then,<br><strong>{safe_tenant}</strong></td></tr>
            </table>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""
    return "\n".join(text_lines), html


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
        "html": html or f"<p>{escape(text).replace(chr(10), '<br>')}</p>",
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
        full_name, service_name, staff_name, start_time, _booking_id = body_params[:5]
        return (
            f"Hi {full_name}, your {service_name} appointment with {staff_name} is confirmed for {start_time}. "
            "Deposits are non-refundable."
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
    text, html = build_booking_confirmation_content(
        client_name=client.full_name,
        tenant_name=tenant.name,
        service_name=service.name,
        staff_name=staff.name,
        start_time=booking.start_time,
        timezone=tenant.timezone,
        manage_url=manage_url,
    )
    await send_and_log_email(
        db,
        booking=booking,
        recipient_type="client",
        notification_type="booking_confirmation",
        to_email=client.email,
        subject=f"Your {service.name} booking is confirmed",
        text=text,
        html=html,
    )
    if client.whatsapp_number:
        await send_and_log_whatsapp(
            db,
            booking=booking,
            recipient_type="client",
            notification_type="booking_confirmation",
            to_number=client.whatsapp_number,
            template_name="booking_confirmation",
            body_params=[client.full_name, service.name, staff.name, format_local_datetime(booking.start_time, tenant.timezone), str(booking.id)],
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
                f"for {format_local_datetime(booking.start_time, tenant.timezone)}."
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
    html: str | None = None,
) -> bool:
    if await notification_already_sent(db, booking.id, recipient_type, "email", notification_type):
        return False
    try:
        sent = await send_email(
            to_email=to_email,
            subject=subject,
            text=text,
            html=html,
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
