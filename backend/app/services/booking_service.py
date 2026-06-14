from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlunparse, urlparse, parse_qs, urlunsplit
from uuid import UUID
import zoneinfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.booking import Booking, BookingInspoAsset, Client
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.schemas.booking import PublicBookingCreateRequest, PublicBookingCreateResponse
from app.services.availability_service import generate_available_slots, load_candidate_staff, load_service
from app.services.booking_management_service import create_manage_token_for_booking, hash_manage_token, manage_url_for_booking
from app.services.inspo_service import save_inspo_images
from app.services.paystack_service import PaystackError
from app.services.payment_provider import initialize_checkout_payment
from app.services.pricing_service import calculate_deposit_due_now, payment_type_for_service, price_status_for_service, requires_deposit_for_booking


async def create_public_booking(
    db: AsyncSession,
    *,
    tenant: Tenant,
    slug: str,
    payload: PublicBookingCreateRequest,
    inspo_images: list | None = None,
) -> PublicBookingCreateResponse:
    service = await load_service(db, tenant.id, payload.service_id)
    deposit_amount = calculate_deposit_due_now(tenant, service)
    payment_type = payment_type_for_service(service)
    if requires_deposit_for_booking(service) and deposit_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "DEPOSIT_REQUIRED", "message": "This service needs a deposit amount before it can be booked online."},
        )
    start_utc = payload.start_time.astimezone(UTC)
    requested_date = payload.start_time.astimezone(zoneinfo.ZoneInfo(tenant.timezone)).date()
    slots = await generate_available_slots(
        db,
        tenant_id=tenant.id,
        service_id=payload.service_id,
        requested_date=requested_date,
        staff_id=payload.staff_id,
    )
    matching_slot = next((slot for slot in slots if slot.start_time == start_utc), None)
    if matching_slot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "SLOT_UNAVAILABLE", "message": "This slot is no longer available."},
        )

    assigned_staff_id = payload.staff_id or await choose_staff_with_fewest_bookings(db, tenant.id, matching_slot.available_staff, start_utc)
    if assigned_staff_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "SLOT_UNAVAILABLE", "message": "No staff member is available for this slot."},
        )

    async with db.begin_nested():
        locked_staff = await lock_staff_for_booking(db, tenant.id, assigned_staff_id, payload.service_id)
        conflict_result = await db.execute(
            select(Booking.id).where(
                Booking.tenant_id == tenant.id,
                Booking.staff_id == assigned_staff_id,
                Booking.start_time == start_utc,
                Booking.status.in_(("pending_payment", "confirmed")),
            )
        )
        if conflict_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "SLOT_UNAVAILABLE", "message": "This slot is no longer available."},
            )

        client_id = await upsert_client(db, tenant.id, payload)
        booking = Booking(
            tenant_id=tenant.id,
            staff_id=assigned_staff_id,
            service_id=service.id,
            client_id=client_id,
            start_time=start_utc,
            end_time=matching_slot.end_time,
            status="pending_payment",
            deposit_amount=deposit_amount,
            price_status=price_status_for_service(service),
            client_notes=payload.notes,
        )
        db.add(booking)
        await db.flush()
        manage_token = create_manage_token_for_booking(booking.id)
        booking.manage_token_hash = hash_manage_token(manage_token)

        inspo_assets: list[BookingInspoAsset] = []
        if inspo_images:
            inspo_assets = await save_inspo_images(tenant_id=tenant.id, booking_id=booking.id, slug=slug, files=inspo_images)
            for asset in inspo_assets:
                db.add(asset)

        reference = f"bk_{booking.id}_{int(datetime.now(UTC).timestamp())}"
        manage_url = manage_url_for_booking(slug, booking.id, manage_token)
        callback_url = f"{str(settings.frontend_url).rstrip('/')}/book/{slug}/verify?booking_id={booking.id}&token={manage_token}"
        try:
            paystack_data, payment_plan = await initialize_checkout_payment(
                email=payload.client.email,
                amount=deposit_amount,
                reference=reference,
                tenant=tenant,
                callback_url=callback_url,
                metadata={
                    "booking_id": str(booking.id),
                    "manage_url": manage_url,
                    "tenant_id": str(tenant.id),
                    "service_name": service.name,
                    "staff_name": locked_staff.name,
                    "start_time": start_utc.isoformat(),
                    "payment_type": payment_type,
                    "deposit_amount": str(deposit_amount),
                },
            )
        except PaystackError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": "PAYSTACK_INIT_FAILED", "message": "Could not initialize payment."},
            ) from None

        payment = Payment(
            booking_id=booking.id,
            tenant_id=tenant.id,
            amount=deposit_amount,
            currency=service.currency,
            paystack_reference=reference,
            paystack_access_code=paystack_data.get("access_code"),
            status="pending",
            payment_type=payment_type,
            provider=payment_plan.provider,
            collection_mode=payment_plan.collection_mode,
            platform_fee_amount=payment_plan.platform_fee_amount,
            business_net_amount=payment_plan.business_net_amount,
            settlement_status="not_due",
        )
        db.add(payment)

    await db.commit()
    # For demo mode, append slug and booking_id to the URL for proper redirect
    payment_url = paystack_data["authorization_url"]
    if payment_url and "/demo/pay?" in payment_url:
        parsed = urlparse(payment_url)
        query_params = parse_qs(parsed.query)
        query_params.update({'slug': [tenant.slug], 'booking_id': [str(booking.id)], 'manage_token': [manage_token]})
        new_query = urlencode(query_params, doseq=True)
        payment_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))
    return PublicBookingCreateResponse(
        booking_id=booking.id,
        payment_url=payment_url,
        reference=reference,
        deposit_amount=deposit_amount,
        manage_url=manage_url,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )


async def lock_staff_for_booking(db: AsyncSession, tenant_id: UUID, staff_id: UUID, service_id: UUID) -> Staff:
    staff_members = await load_candidate_staff(db, tenant_id=tenant_id, service_id=service_id, staff_id=staff_id)
    if not staff_members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "STAFF_NOT_AVAILABLE", "message": "Staff member is unavailable."})
    result = await db.execute(select(Staff).where(Staff.tenant_id == tenant_id, Staff.id == staff_id).with_for_update())
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "STAFF_NOT_FOUND", "message": "Staff member was not found."})
    return staff


async def upsert_client(db: AsyncSession, tenant_id: UUID, payload: PublicBookingCreateRequest) -> UUID:
    stmt = (
        insert(Client)
        .values(
            tenant_id=tenant_id,
            email=payload.client.email.lower(),
            full_name=payload.client.full_name,
            phone=payload.client.phone,
            whatsapp_number=payload.client.whatsapp_number,
        )
        .on_conflict_do_update(
            index_elements=[Client.tenant_id, Client.email],
            set_={
                "full_name": payload.client.full_name,
                "phone": payload.client.phone,
                "whatsapp_number": payload.client.whatsapp_number,
                "updated_at": datetime.now(UTC),
            },
        )
        .returning(Client.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def choose_staff_with_fewest_bookings(db: AsyncSession, tenant_id: UUID, staff_ids: tuple[UUID, ...], start_time: datetime) -> UUID | None:
    if not staff_ids:
        return None
    counts: dict[UUID, int] = {staff_id: 0 for staff_id in staff_ids}
    day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    result = await db.execute(
        select(Booking.staff_id, func.count(Booking.id))
        .where(
            Booking.tenant_id == tenant_id,
            Booking.staff_id.in_(staff_ids),
            Booking.start_time >= day_start,
            Booking.start_time < day_end,
            Booking.status.in_(("pending_payment", "confirmed")),
        )
        .group_by(Booking.staff_id)
    )
    for staff_id, count in result.all():
        counts[staff_id] = count
    return min(counts, key=counts.get)
