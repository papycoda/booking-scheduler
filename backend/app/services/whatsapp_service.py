from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from email.utils import parseaddr
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.booking import Booking
from app.models.booking import Client
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.booking import PublicBookingCreateRequest, ClientBookingRequest
from app.services.assistant_service import (
    answer_business_location,
    answer_deposit_policy,
    answer_list_services,
    answer_service_duration,
    answer_service_price,
    answer_public_assistant_message,
    find_matching_service,
    format_duration,
    format_ngn,
    format_slot_time,
    join_names,
    load_active_services,
    normalize_text,
)
from app.services.availability_service import generate_available_slots
from app.services.booking_service import create_public_booking
from app.services.notification_service import send_whatsapp_message
from app.services.payment_provider import initialize_checkout_payment

logger = logging.getLogger(__name__)

BOOKING_STATES = {
    "collecting_booking_details",
    "awaiting_time_choice",
    "awaiting_checkout_email",
    "awaiting_atomic_confirmation",
    "payment_link_pending",
    "handoff_pending",
    "human_active",
    "closed",
}

HANDOFF_PHRASES = ("human", "agent", "person", "staff", "owner", "representative")
CONFIRM_PHRASES = ("confirm", "confirmed", "yes confirm", "send it", "go ahead", "book it")


@dataclass(frozen=True)
class InboundOutcome:
    reply: str | None
    state: str
    status: str
    booking_context: dict[str, Any]
    summary: str | None = None
    booking_id: UUID | None = None
    customer_name: str | None = None


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^0-9+]", "", value.strip())
    if cleaned.startswith("whatsapp:"):
        cleaned = cleaned[len("whatsapp:") :]
    if cleaned.startswith("00"):
        cleaned = f"+{cleaned[2:]}"
    if cleaned and not cleaned.startswith("+"):
        cleaned = f"+{cleaned}"
    return cleaned


def strip_whatsapp_prefix(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("whatsapp:", "", 1) if value.startswith("whatsapp:") else value


def human_reply(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_handoff_request(message: str) -> bool:
    text = normalize_text(message)
    return any(phrase in text for phrase in HANDOFF_PHRASES)


def is_confirm_message(message: str) -> bool:
    text = normalize_text(message)
    return text in CONFIRM_PHRASES


def extract_email(message: str) -> str | None:
    candidate = parseaddr(message)[1].strip().lower()
    if candidate and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", candidate):
        return candidate
    return None


def extract_name(message: str) -> str | None:
    text = message.strip()
    normalized = normalize_text(text)
    if len(text) < 2 or "@" in text or re.search(r"\d", text):
        return None
    if normalized.startswith("my name is "):
        candidate = text.split("is", 1)[1].strip()
        return candidate[:255] if candidate else None
    if len(text.split()) > 3:
        return None
    if any(keyword in normalized for keyword in ("book", "service", "price", "available", "today", "tomorrow", "deposit", "cancel", "confirm", "where")):
        return None
    if normalized in {"yes", "confirm", "ok", "okay", "thanks", "thank you"}:
        return None
    return text[:255]


def extract_date(message: str, tenant: Tenant) -> date | None:
    text = normalize_text(message)
    today = datetime.now(UTC).astimezone(ZoneInfo(tenant.timezone)).date()
    if "today" in text:
        return today
    if "tomorrow" in text:
        return today + timedelta(days=1)
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", message)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def extract_time_candidate(message: str) -> time | None:
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", message, flags=re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = (match.group(3) or "").lower()
    if suffix == "pm" and hour != 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return time(hour=hour, minute=minute)


async def get_or_create_conversation(db: AsyncSession, *, tenant: Tenant, customer_phone: str, customer_name: str | None = None) -> WhatsAppConversation:
    result = await db.execute(
        select(WhatsAppConversation).where(
            WhatsAppConversation.tenant_id == tenant.id,
            WhatsAppConversation.customer_phone == customer_phone,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is not None:
        if customer_name and not conversation.customer_name:
            conversation.customer_name = customer_name
        return conversation
    conversation = WhatsAppConversation(
        tenant_id=tenant.id,
        customer_phone=customer_phone,
        customer_name=customer_name,
        status="open",
        state="collecting_booking_details",
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def record_message(
    db: AsyncSession,
    *,
    tenant: Tenant,
    conversation: WhatsAppConversation,
    direction: str,
    author_type: str,
    body: str,
    provider_message_id: str | None = None,
    status: str = "received",
    sender_user_id: UUID | None = None,
) -> WhatsAppMessage:
    message = WhatsAppMessage(
        tenant_id=tenant.id,
        conversation_id=conversation.id,
        direction=direction,
        author_type=author_type,
        body=body,
        provider_message_id=provider_message_id,
        status=status,
        sender_user_id=sender_user_id,
    )
    db.add(message)
    conversation.last_message_at = datetime.now(UTC)
    if direction == "inbound":
        conversation.last_inbound_at = datetime.now(UTC)
    else:
        conversation.last_outbound_at = datetime.now(UTC)
    await db.flush()
    return message


async def send_outbound_message(
    db: AsyncSession,
    *,
    tenant: Tenant,
    conversation: WhatsAppConversation,
    body: str,
    sender_user_id: UUID | None = None,
) -> WhatsAppMessage:
    message = await record_message(
        db,
        tenant=tenant,
        conversation=conversation,
        direction="outbound",
        author_type="assistant" if sender_user_id is None else "owner",
        body=body,
        sender_user_id=sender_user_id,
        status="queued",
    )
    try:
        provider_id = await send_whatsapp_message(to_number=conversation.customer_phone, body=body)
        message.provider_message_id = provider_id
        if provider_id:
            message.status = "sent"
            message.sent_at = datetime.now(UTC)
        await db.commit()
    except Exception as exc:
        logger.exception("WhatsApp outbound message failed")
        message.status = "failed"
        message.metadata_ = {"error": str(exc)}
        await db.commit()
    return message


async def send_and_track_reply(db: AsyncSession, *, tenant: Tenant, conversation: WhatsAppConversation, reply: str | None, sender_user_id: UUID | None = None) -> None:
    if not reply:
        return
    await send_outbound_message(db, tenant=tenant, conversation=conversation, body=reply, sender_user_id=sender_user_id)


async def build_context_prompt(tenant: Tenant) -> str:
    parts = [
        tenant.front_desk_intro,
        tenant.front_desk_hours,
        tenant.front_desk_service_areas,
        tenant.front_desk_prep_notes,
        tenant.front_desk_policies,
        tenant.front_desk_escalation_rules,
    ]
    return "\n".join(part.strip() for part in parts if part and part.strip())


async def generate_booking_reply(db: AsyncSession, *, tenant: Tenant, conversation: WhatsAppConversation, message: str) -> InboundOutcome:
    context = conversation.booking_context or {}
    services = await load_active_services(db, tenant.id)
    customer_name = conversation.customer_name

    if is_handoff_request(message):
        return InboundOutcome(
            reply="I’ve sent this to the team. A human will take over here shortly.",
            state="handoff_pending",
            status="human_active",
            booking_context=context,
            customer_name=customer_name,
        )

    if conversation.status == "human_active" or conversation.state == "human_active":
        return InboundOutcome(reply=None, state="human_active", status="human_active", booking_context=context, customer_name=customer_name)

    if customer_name is None:
        possible_name = extract_name(message)
        if possible_name:
            customer_name = possible_name
            context["customer_name"] = customer_name

    service = None
    if context.get("service_id"):
        try:
            service_id = UUID(str(context["service_id"]))
            service = next((item for item in services if item.id == service_id), None)
        except ValueError:
            service = None

    matched_service = find_matching_service(message, services, service.id if service else None)
    if matched_service is not None:
        service = matched_service
        context["service_id"] = str(service.id)
        context["service_name"] = service.name

    if service is None:
        response = await answer_public_assistant_message(db, tenant=tenant, slug=tenant.slug, payload=__import__("app.schemas.assistant", fromlist=["AssistantRequest"]).AssistantRequest(message=message))
        return InboundOutcome(
            reply=response.reply,
            state="collecting_booking_details",
            status="open",
            booking_context=context,
            customer_name=customer_name,
        )

    if "requested_date" not in context:
        requested_date = extract_date(message, tenant)
        if requested_date is None:
            reply = f"Which date would you like for {service.name}? You can say today, tomorrow, or a date like 2026-07-21."
            return InboundOutcome(reply=reply, state="collecting_booking_details", status="open", booking_context=context, customer_name=customer_name)
        context["requested_date"] = requested_date.isoformat()

    requested_date = date.fromisoformat(str(context["requested_date"]))
    slots = await generate_available_slots(db, tenant_id=tenant.id, service_id=service.id, requested_date=requested_date)
    if not slots:
        return InboundOutcome(
            reply=f"I couldn’t find open times for {service.name} on {requested_date.isoformat()}. Try another date.",
            state="collecting_booking_details",
            status="open",
            booking_context=context,
            customer_name=customer_name,
        )

    selected_start = context.get("selected_start_time")
    time_candidate = extract_time_candidate(message)
    if selected_start is None and time_candidate is not None:
        match = next((slot for slot in slots if slot.start_time.astimezone(ZoneInfo(tenant.timezone)).time().replace(second=0, microsecond=0) == time_candidate.replace(second=0, microsecond=0)), None)
        if match is not None:
            context["selected_start_time"] = match.start_time.isoformat()
            context["selected_end_time"] = match.end_time.isoformat()
            selected_start = context["selected_start_time"]

    if selected_start is None and normalize_text(message).isdigit():
        index = int(normalize_text(message)) - 1
        if 0 <= index < len(slots):
            slot = slots[index]
            context["selected_start_time"] = slot.start_time.isoformat()
            context["selected_end_time"] = slot.end_time.isoformat()
            selected_start = context["selected_start_time"]

    if selected_start is None:
        slot_labels = [f"{index + 1}. {format_slot_time(slot.start_time, tenant.timezone)}" for index, slot in enumerate(slots[:5])]
        context["slot_options"] = [slot.start_time.isoformat() for slot in slots[:5]]
        reply = f"I found these times for {service.name} on {requested_date.isoformat()}: {join_names(slot_labels)}. Reply with the number or exact time you want."
        return InboundOutcome(reply=reply, state="awaiting_time_choice", status="open", booking_context=context, customer_name=customer_name)

    if not customer_name:
        reply = "What name should I use for the booking?"
        return InboundOutcome(reply=reply, state="awaiting_checkout_email", status="open", booking_context=context, customer_name=customer_name)

    if "email" not in context:
        email = extract_email(message)
        if email is None:
            reply = "What email should I use to send your payment link?"
            context["customer_name"] = customer_name
            return InboundOutcome(reply=reply, state="awaiting_checkout_email", status="open", booking_context=context, customer_name=customer_name)
        context["email"] = email

    start_time = datetime.fromisoformat(str(context["selected_start_time"]))
    end_time = datetime.fromisoformat(str(context["selected_end_time"]))
    deposit_amount = None
    selected_service = service
    if selected_service is not None:
        from app.services.pricing_service import calculate_deposit_due_now

        deposit_amount = calculate_deposit_due_now(tenant, selected_service)
    summary = (
        f"Please confirm your booking: {selected_service.name} on {start_time.astimezone(ZoneInfo(tenant.timezone)).strftime('%A, %d %B %Y at %I:%M %p').lstrip('0')} "
        f"for {customer_name}. Deposit due now is NGN {format_ngn(deposit_amount or 0)}. Reply CONFIRM to reserve the slot and generate your payment link."
    )
    context["summary"] = summary
    return InboundOutcome(reply=summary, state="awaiting_atomic_confirmation", status="open", booking_context=context, summary=summary, customer_name=customer_name)


async def confirm_booking(
    db: AsyncSession,
    *,
    tenant: Tenant,
    conversation: WhatsAppConversation,
    message: str,
) -> InboundOutcome:
    context = conversation.booking_context or {}
    customer_name = context.get("customer_name") or conversation.customer_name
    email = context.get("email")
    service_id = context.get("service_id")
    start_time = context.get("selected_start_time")

    if not (customer_name and email and service_id and start_time):
        return InboundOutcome(
            reply="I still need the booking details. Please share the service, date, time, name, and email.",
            state="collecting_booking_details",
            status="open",
            booking_context=context,
            customer_name=customer_name,
        )

    if not is_confirm_message(message):
        return InboundOutcome(
            reply="Reply CONFIRM to reserve the slot and generate your payment link.",
            state="awaiting_atomic_confirmation",
            status="open",
            booking_context=context,
            customer_name=customer_name,
            summary=context.get("summary"),
        )

    service_result = await db.execute(select(Service).where(Service.tenant_id == tenant.id, Service.id == UUID(str(service_id))))
    service = service_result.scalar_one_or_none()
    if service is None:
        return InboundOutcome(
            reply="I could not find that service anymore. Please start again with the service name.",
            state="collecting_booking_details",
            status="open",
            booking_context={},
            customer_name=customer_name,
        )

    start_dt = datetime.fromisoformat(str(start_time))
    end_dt = datetime.fromisoformat(str(context.get("selected_end_time")))
    payload = PublicBookingCreateRequest(
        service_id=service.id,
        staff_id=None,
        start_time=start_dt,
        client=ClientBookingRequest(
            full_name=str(customer_name),
            email=str(email),
            phone=normalize_phone(conversation.customer_phone),
            whatsapp_number=normalize_phone(conversation.customer_phone),
        ),
        notes=str(context.get("notes")) if context.get("notes") else None,
    )
    response = await create_public_booking(db, tenant=tenant, slug=tenant.slug, payload=payload)
    context["booking_id"] = str(response.booking_id)
    context["payment_url"] = response.payment_url
    context["manage_url"] = response.manage_url
    context["reference"] = response.reference
    conversation.booking_id = response.booking_id
    conversation.summary = context.get("summary")
    if response.payment_url:
        reply = f"Booked. Here is your payment link: {response.payment_url}"
        return InboundOutcome(reply=reply, state="closed", status="closed", booking_context=context, summary=conversation.summary, booking_id=response.booking_id, customer_name=str(customer_name))
    reply = response.payment_message or "Booked. I’m preparing your payment link and will send it here shortly."
    return InboundOutcome(reply=reply, state="payment_link_pending", status="open", booking_context=context, summary=conversation.summary, booking_id=response.booking_id, customer_name=str(customer_name))


async def process_inbound_whatsapp_message(
    db: AsyncSession,
    *,
    tenant: Tenant,
    conversation: WhatsAppConversation,
    message: str,
) -> InboundOutcome:
    trimmed = message.strip()
    if conversation.state == "awaiting_atomic_confirmation":
        return await confirm_booking(db, tenant=tenant, conversation=conversation, message=trimmed)
    return await generate_booking_reply(db, tenant=tenant, conversation=conversation, message=trimmed)


async def handle_inbound_whatsapp_message(
    db: AsyncSession,
    *,
    tenant: Tenant,
    from_number: str,
    profile_name: str | None,
    message_sid: str | None,
    body: str,
) -> str | None:
    conversation = await get_or_create_conversation(db, tenant=tenant, customer_phone=from_number, customer_name=profile_name)
    if message_sid:
        existing = await db.execute(
            select(WhatsAppMessage.id).where(
                WhatsAppMessage.tenant_id == tenant.id,
                WhatsAppMessage.provider_message_id == message_sid,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None

    await record_message(
        db,
        tenant=tenant,
        conversation=conversation,
        direction="inbound",
        author_type="customer",
        body=body,
        provider_message_id=message_sid,
        status="received",
    )

    if conversation.state == "human_active":
        await db.commit()
        return None

    outcome = await process_inbound_whatsapp_message(db, tenant=tenant, conversation=conversation, message=body)
    conversation.state = outcome.state
    conversation.status = outcome.status
    conversation.booking_context = outcome.booking_context
    conversation.summary = outcome.summary
    if outcome.customer_name:
        conversation.customer_name = outcome.customer_name
    if outcome.booking_id is not None:
        conversation.booking_id = outcome.booking_id
    await db.commit()
    await send_and_track_reply(db, tenant=tenant, conversation=conversation, reply=outcome.reply)
    return outcome.reply


async def retry_pending_payment_initializations(db: AsyncSession) -> int:
    result = await db.execute(
        select(Payment, Booking, Tenant, Service, Staff, Client)
        .join(Booking, Booking.id == Payment.booking_id)
        .join(Tenant, Tenant.id == Payment.tenant_id)
        .join(Service, Service.id == Booking.service_id)
        .join(Staff, Staff.id == Booking.staff_id)
        .join(Client, Client.id == Booking.client_id)
        .where(Payment.status == "pending", Payment.checkout_url.is_(None))
        .order_by(Payment.created_at.asc())
        .limit(20)
    )
    count = 0
    changed = False
    for payment, booking, tenant, service, staff, client in result.all():
        if booking.status != "pending_payment":
            continue
        try:
            conversation_result = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.booking_id == booking.id))
            conversation = conversation_result.scalar_one_or_none()
            callback_url = f"{str(settings.frontend_url).rstrip('/')}/book/{tenant.slug}/verify?booking_id={booking.id}&token={booking.manage_token_hash or ''}"
            paystack_data, payment_plan = await initialize_checkout_payment(
                email=client.email,
                amount=payment.amount,
                reference=payment.paystack_reference,
                tenant=tenant,
                callback_url=callback_url,
                metadata={
                    "booking_id": str(booking.id),
                    "manage_url": "",
                    "tenant_id": str(tenant.id),
                    "service_name": service.name,
                    "staff_name": staff.name,
                    "start_time": booking.start_time.isoformat(),
                    "payment_type": payment.payment_type,
                    "deposit_amount": str(payment.amount),
                },
            )
            checkout_url = paystack_data["authorization_url"]
            payment.checkout_url = checkout_url
            payment.paystack_access_code = paystack_data.get("access_code")
            payment.provider = payment_plan.provider
            payment.collection_mode = payment_plan.collection_mode
            payment.platform_fee_amount = payment_plan.platform_fee_amount
            payment.business_net_amount = payment_plan.business_net_amount
            payment.initialization_error = None
            payment.initialization_attempts = (payment.initialization_attempts or 0) + 1
            payment.last_initialization_attempt_at = datetime.now(UTC)
            count += 1
            changed = True
            if conversation is not None and conversation.customer_phone:
                await send_outbound_message(db, tenant=tenant, conversation=conversation, body=f"Your payment link for {service.name} is ready: {checkout_url}")
        except Exception as exc:
            logger.info("Could not retry payment initialization for booking %s: %s", booking.id, exc)
            payment.initialization_error = str(exc)
            payment.initialization_attempts = (payment.initialization_attempts or 0) + 1
            payment.last_initialization_attempt_at = datetime.now(UTC)
            changed = True
    if changed:
        await db.commit()
    return count
