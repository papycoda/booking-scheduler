import re
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.models.tenant import Tenant
from app.schemas.assistant import AssistantIntent, AssistantRequest, AssistantResponse, AssistantSuggestedAction
from app.services.availability_service import generate_available_slots
from app.services.pricing_service import calculate_deposit_due_now, price_label_for_service

SAFE_UNKNOWN_REPLY = "I dont have that information yet. You can continue with the booking page or contact the business directly."
FALLBACK_REPLY = "I can help with services, prices, availability, deposits, location, and booking. What would you like to know?"


async def answer_public_assistant_message(
    db: AsyncSession,
    *,
    tenant: Tenant,
    slug: str,
    payload: AssistantRequest,
) -> AssistantResponse:
    message = payload.message.strip()
    intent = detect_intent(message)
    services = await load_active_services(db, tenant.id)
    context = payload.context
    matched_service = find_matching_service(message, services, context.service_id if context else None)

    if intent == "list_services":
        return answer_list_services(services)
    if intent == "service_price":
        return answer_service_price(tenant, services, matched_service)
    if intent == "service_duration":
        return answer_service_duration(services, matched_service)
    if intent == "available_slots":
        selected_date = context.selected_date if context else None
        return await answer_availability(db, tenant, matched_service, message, selected_date)
    if intent == "business_location":
        return answer_business_location(tenant)
    if intent == "deposit_policy":
        return answer_deposit_policy(tenant, matched_service)
    if intent == "cancellation_policy":
        return AssistantResponse(
            intent="cancellation_policy",
            reply=f"You can cancel, but please do it at least {tenant.cancellation_notice_hours} hours before your appointment.",
        )
    if intent == "reschedule_policy":
        return AssistantResponse(
            intent="reschedule_policy",
            reply="You can request a reschedule from your booking management link after booking. The business will approve or reject the request.",
            suggested_actions=[book_now_action()],
        )
    if intent == "how_to_book":
        return AssistantResponse(
            intent="how_to_book",
            reply="Choose a service, pick an available time, enter your details, and pay the deposit to confirm.",
            suggested_actions=[book_now_action()],
        )
    return AssistantResponse(intent="fallback", reply=FALLBACK_REPLY, suggested_actions=[book_now_action()])


async def load_active_services(db: AsyncSession, tenant_id: UUID) -> list[Service]:
    result = await db.execute(select(Service).where(Service.tenant_id == tenant_id, Service.is_active.is_(True)).order_by(Service.name))
    services = list(result.scalars().all())
    return [service for service in services if service.tenant_id == tenant_id and service.is_active]


def detect_intent(message: str) -> AssistantIntent:
    normalized = normalize_text(message)
    if has_any(normalized, ("cancel", "cancellation")):
        return "cancellation_policy"
    if has_any(normalized, ("reschedule", "change my time", "change time")):
        return "reschedule_policy"
    if has_any(normalized, ("deposit", "pay later", "due now")):
        return "deposit_policy"
    if has_any(normalized, ("where", "address", "location", "located")):
        return "business_location"
    if has_any(normalized, ("available", "availability", "free", "slot", "today", "tomorrow", "saturday", "sunday", "weekend", "come by")):
        return "available_slots"
    if has_any(normalized, ("how much", "price", "cost", "fee")):
        return "service_price"
    if has_any(normalized, ("how long", "duration", "hours", "hour", "minutes", "minute")):
        return "service_duration"
    if has_any(normalized, ("what services", "services", "offer", "what can i book", "show me your services")):
        return "list_services"
    if has_any(normalized, ("how do i book", "how can i make appointment", "appointment", "how do i pay", "book now")):
        return "how_to_book"
    return "fallback"


def has_any(normalized: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def find_matching_service(message: str, services: list[Service], context_service_id: UUID | None = None) -> Service | None:
    if context_service_id is not None:
        context_match = next((service for service in services if service.id == context_service_id), None)
        if context_match is not None:
            return context_match

    normalized_message = normalize_text(message)
    compact_message = compact_text(message)
    for service in services:
        normalized_name = normalize_text(service.name)
        if normalized_name and normalized_name in normalized_message:
            return service
    for service in services:
        compact_name = compact_text(service.name)
        if compact_name and compact_name in compact_message:
            return service
    return None


def answer_list_services(services: list[Service]) -> AssistantResponse:
    if not services:
        return AssistantResponse(intent="list_services", reply=SAFE_UNKNOWN_REPLY, suggested_actions=[book_now_action()])
    names = join_names([service.name for service in services])
    actions = [service_action(service) for service in services[:5]]
    actions.append(book_now_action())
    return AssistantResponse(
        intent="list_services",
        reply=f"We offer {names}. You can select any service on this page to see available times.",
        suggested_actions=actions,
    )


def answer_service_price(tenant: Tenant, services: list[Service], service: Service | None) -> AssistantResponse:
    if service is None:
        return clarification_response("service_price", services)
    deposit_due = calculate_deposit_due_now(tenant, service)
    parts = [f"{service.name} {price_label_for_service(service)}."]
    if deposit_due > 0:
        parts.append(f"Deposit due now is NGN {format_ngn(deposit_due)}.")
    parts.append(f"It takes about {format_duration(service.duration_minutes)}.")
    return AssistantResponse(intent="service_price", reply=" ".join(parts), suggested_actions=[service_action(service), book_now_action()])


def answer_service_duration(services: list[Service], service: Service | None) -> AssistantResponse:
    if service is None:
        return clarification_response("service_duration", services)
    return AssistantResponse(
        intent="service_duration",
        reply=f"{service.name} takes about {format_duration(service.duration_minutes)}.",
        suggested_actions=[service_action(service), book_now_action()],
    )


async def answer_availability(
    db: AsyncSession,
    tenant: Tenant,
    service: Service | None,
    message: str,
    selected_date,
) -> AssistantResponse:
    if service is None:
        return AssistantResponse(intent="available_slots", reply="Which service would you like to book? Availability depends on the service.")

    requested_date = resolve_requested_date(message, selected_date, tenant)
    if requested_date is None:
        return AssistantResponse(
            intent="available_slots",
            reply="Please choose a date on the booking page first. I can check availability for today, tomorrow, or the selected date.",
            suggested_actions=[service_action(service), book_now_action()],
        )

    try:
        slots = await generate_available_slots(db, tenant_id=tenant.id, service_id=service.id, requested_date=requested_date)
    except HTTPException:
        return AssistantResponse(
            intent="available_slots",
            reply="I could not find available times for that date. Please choose another date on the booking page.",
            suggested_actions=[service_action(service), book_now_action()],
        )

    visible_slots = slots[:5]
    if not visible_slots:
        return AssistantResponse(
            intent="available_slots",
            reply=f"I did not find open times for {service.name} on {requested_date.isoformat()}. Try another date on the booking page.",
            suggested_actions=[service_action(service), book_now_action()],
        )

    slot_labels = [format_slot_time(slot.start_time, tenant.timezone) for slot in visible_slots]
    date_label = relative_date_label(requested_date, tenant)
    actions = [
        AssistantSuggestedAction(type="show_slots", label=label, service_id=service.id, start_time=slot.start_time)
        for label, slot in zip(slot_labels, visible_slots, strict=False)
    ]
    actions.append(book_now_action())
    return AssistantResponse(
        intent="available_slots",
        reply=f"I found these available times for {service.name} {date_label}: {join_names(slot_labels)}.",
        suggested_actions=actions,
    )


def answer_business_location(tenant: Tenant) -> AssistantResponse:
    if tenant.address:
        return AssistantResponse(intent="business_location", reply=f"{tenant.name} is located at {tenant.address}.")
    return AssistantResponse(intent="business_location", reply="The business has not added an address yet.")


def answer_deposit_policy(tenant: Tenant, service: Service | None) -> AssistantResponse:
    if service is not None:
        deposit_due = calculate_deposit_due_now(tenant, service)
        if deposit_due > 0:
            return AssistantResponse(
                intent="deposit_policy",
                reply=f"Yes. A deposit is required to confirm {service.name}. Deposit due now is NGN {format_ngn(deposit_due)}.",
                suggested_actions=[service_action(service), book_now_action()],
            )
        return AssistantResponse(
            intent="deposit_policy",
            reply=f"{service.name} does not currently show a deposit due now. The amount due will be shown before payment.",
            suggested_actions=[service_action(service), book_now_action()],
        )
    if tenant.default_deposit_amount > 0:
        return AssistantResponse(
            intent="deposit_policy",
            reply=f"Yes. A deposit is required to confirm your booking. The default deposit due now is NGN {format_ngn(tenant.default_deposit_amount)}.",
            suggested_actions=[book_now_action()],
        )
    return AssistantResponse(
        intent="deposit_policy",
        reply="The amount due now will be shown before payment after you choose a service.",
        suggested_actions=[book_now_action()],
    )


def resolve_requested_date(message: str, selected_date, tenant: Tenant):
    normalized = normalize_text(message)
    tenant_today = datetime.now(UTC).astimezone(ZoneInfo(tenant.timezone)).date()
    if "today" in normalized:
        return tenant_today
    if "tomorrow" in normalized:
        return tenant_today + timedelta(days=1)
    if selected_date is not None:
        return selected_date
    return None


def relative_date_label(requested_date, tenant: Tenant) -> str:
    tenant_today = datetime.now(UTC).astimezone(ZoneInfo(tenant.timezone)).date()
    if requested_date == tenant_today:
        return "today"
    if requested_date == tenant_today + timedelta(days=1):
        return "tomorrow"
    return f"on {requested_date.isoformat()}"


def service_action(service: Service) -> AssistantSuggestedAction:
    return AssistantSuggestedAction(type="view_service", label=f"View {service.name}", service_id=service.id)


def book_now_action() -> AssistantSuggestedAction:
    return AssistantSuggestedAction(type="book_now", label="Book now")


def clarification_response(intent: AssistantIntent, services: list[Service]) -> AssistantResponse:
    if not services:
        return AssistantResponse(intent=intent, reply=SAFE_UNKNOWN_REPLY, suggested_actions=[book_now_action()])
    names = join_names([service.name for service in services])
    return AssistantResponse(
        intent=intent,
        reply=f"Which service do you mean? You can choose from: {names}.",
        suggested_actions=[service_action(service) for service in services[:5]],
    )


def join_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def format_ngn(amount_kobo: int) -> str:
    return f"{int(amount_kobo) / 100:,.0f}"


def format_duration(minutes: int) -> str:
    hours, remaining_minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if remaining_minutes:
        parts.append(f"{remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}")
    return " ".join(parts) if parts else "0 minutes"


def format_slot_time(value: datetime, timezone: str) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo(timezone)).strftime("%I:%M %p").lstrip("0")
