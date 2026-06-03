from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.booking import Booking, BookingInspoAsset, BookingRescheduleRequest, Client
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff
from app.models.user import User
from app.schemas.dashboard import (
    AnalyticsOverviewResponse,
    DashboardBookingResponse,
    DashboardBookingStatusUpdate,
    DashboardPayoutDetailResponse,
    DashboardPayoutResponse,
    DashboardRescheduleDecision,
    DashboardRescheduleRequestResponse,
)
from app.services.booking_management_service import decide_reschedule_request, dashboard_reschedule_row_to_response
from app.services.settlement_service import approve_payout, initiate_platform_collected_payout

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def booking_row_to_response(row, assets_by_booking: dict[UUID, list[BookingInspoAsset]] | None = None) -> DashboardBookingResponse:
    booking, client, service, staff, payment = row
    assets = assets_by_booking.get(booking.id, []) if assets_by_booking else []
    return DashboardBookingResponse(
        id=booking.id,
        payment_id=getattr(payment, "id", None) if payment else None,
        status=booking.status,
        start_time=booking.start_time,
        end_time=booking.end_time,
        client_name=client.full_name,
        client_email=client.email,
        service_name=service.name,
        staff_name=staff.name,
        amount=payment.amount if payment else None,
        payment_status=payment.status if payment else None,
        collection_mode=getattr(payment, "collection_mode", None) if payment else None,
        platform_fee_amount=getattr(payment, "platform_fee_amount", None) if payment else None,
        business_net_amount=getattr(payment, "business_net_amount", None) if payment else None,
        settlement_status=getattr(payment, "settlement_status", None) if payment else None,
        deposit_amount=getattr(booking, "deposit_amount", payment.amount if payment else 0),
        price_status=getattr(booking, "price_status", "fixed"),
        quoted_price=getattr(booking, "quoted_price", None),
        client_notes=getattr(booking, "client_notes", None),
        cancellation_reason=getattr(booking, "cancellation_reason", None),
        cancelled_by=getattr(booking, "cancelled_by", None),
        inspo_assets=[
            {
                "id": str(asset.id),
                "original_filename": asset.original_filename,
                "content_type": asset.content_type,
                "size_bytes": asset.size_bytes,
                "url": asset.url,
            }
            for asset in assets
        ],
    )


def booking_detail_stmt(tenant_id: UUID):
    return (
        select(Booking, Client, Service, Staff, Payment)
        .join(Client, Client.id == Booking.client_id)
        .join(Service, Service.id == Booking.service_id)
        .join(Staff, Staff.id == Booking.staff_id)
        .join(Payment, Payment.booking_id == Booking.id, isouter=True)
        .where(Booking.tenant_id == tenant_id)
    )


@router.get("/bookings", response_model=list[DashboardBookingResponse])
async def list_dashboard_bookings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    booking_status: Annotated[str | None, Query(alias="status")] = None,
    booking_date: Annotated[date | None, Query(alias="date")] = None,
    staff_id: UUID | None = None,
) -> list[DashboardBookingResponse]:
    stmt = booking_detail_stmt(current_user.tenant_id)
    if booking_status is not None:
        stmt = stmt.where(Booking.status == booking_status)
    if staff_id is not None:
        stmt = stmt.where(Booking.staff_id == staff_id)
    if booking_date is not None:
        day_start = datetime.combine(booking_date, datetime.min.time(), UTC)
        stmt = stmt.where(Booking.start_time >= day_start, Booking.start_time < day_start + timedelta(days=1))
    stmt = stmt.order_by(Booking.start_time.desc())
    result = await db.execute(stmt)
    rows = result.all()
    assets_by_booking = await load_inspo_assets(db, [row[0].id for row in rows])
    return [booking_row_to_response(row, assets_by_booking) for row in rows]


@router.get("/bookings/{booking_id}", response_model=DashboardBookingResponse)
async def get_dashboard_booking(
    booking_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardBookingResponse:
    result = await db.execute(booking_detail_stmt(current_user.tenant_id).where(Booking.id == booking_id))
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    assets_by_booking = await load_inspo_assets(db, [booking_id])
    return booking_row_to_response(row, assets_by_booking)


@router.patch("/bookings/{booking_id}", response_model=DashboardBookingResponse)
async def update_dashboard_booking(
    booking_id: UUID,
    payload: DashboardBookingStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardBookingResponse:
    booking_result = await db.execute(select(Booking).where(Booking.tenant_id == current_user.tenant_id, Booking.id == booking_id))
    booking = booking_result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "BOOKING_NOT_FOUND", "message": "Booking was not found."})
    booking.status = payload.status
    if payload.status == "cancelled":
        booking.cancelled_by = "business"
        booking.cancelled_at = datetime.now(UTC)
        booking.cancellation_reason = payload.cancellation_reason
    if payload.quoted_price is not None:
        booking.quoted_price = payload.quoted_price
        booking.price_status = "quoted"
    await db.commit()
    result = await db.execute(booking_detail_stmt(current_user.tenant_id).where(Booking.id == booking_id))
    assets_by_booking = await load_inspo_assets(db, [booking_id])
    return booking_row_to_response(result.one(), assets_by_booking)


@router.get("/reschedule-requests", response_model=list[DashboardRescheduleRequestResponse])
async def list_reschedule_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_history: bool = False,
) -> list[DashboardRescheduleRequestResponse]:
    from sqlalchemy.orm import aliased

    current_staff = aliased(Staff)
    requested_staff = aliased(Staff)
    stmt = (
        select(BookingRescheduleRequest, Booking, Client, Service, current_staff, requested_staff)
        .join(Booking, Booking.id == BookingRescheduleRequest.booking_id)
        .join(Client, Client.id == Booking.client_id)
        .join(Service, Service.id == Booking.service_id)
        .join(current_staff, current_staff.id == Booking.staff_id)
        .join(requested_staff, requested_staff.id == BookingRescheduleRequest.requested_staff_id)
        .where(BookingRescheduleRequest.tenant_id == current_user.tenant_id)
        .order_by(BookingRescheduleRequest.created_at.desc())
    )
    if not include_history:
        stmt = stmt.where(BookingRescheduleRequest.status == "pending", BookingRescheduleRequest.hold_expires_at > datetime.now(UTC))
    result = await db.execute(stmt)
    return [dashboard_reschedule_row_to_response(row) for row in result.all()]


@router.post("/reschedule-requests/{request_id}/decision", status_code=204)
async def decide_dashboard_reschedule_request(
    request_id: UUID,
    payload: DashboardRescheduleDecision,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await decide_reschedule_request(
        db,
        tenant_id=current_user.tenant_id,
        request_id=request_id,
        user_id=current_user.id,
        decision=payload.decision,
        note=payload.note,
    )


@router.post("/payments/{payment_id}/payout", response_model=DashboardPayoutResponse)
async def initiate_dashboard_payout(
    payment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardPayoutResponse:
    payment = await initiate_platform_collected_payout(db, tenant_id=current_user.tenant_id, payment_id=payment_id)
    return DashboardPayoutResponse(
        payment_id=payment.id,
        settlement_status=payment.settlement_status,
        payout_transfer_reference=payment.payout_transfer_reference,
        payout_transfer_code=payment.payout_transfer_code,
    )


@router.get("/payouts", response_model=list[DashboardPayoutDetailResponse])
async def list_dashboard_payouts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DashboardPayoutDetailResponse]:
    result = await db.execute(
        select(Payment, Booking, Client, Service)
        .join(Booking, Booking.id == Payment.booking_id)
        .join(Client, Client.id == Booking.client_id)
        .join(Service, Service.id == Booking.service_id)
        .where(Payment.tenant_id == current_user.tenant_id, Payment.collection_mode == "platform_collected")
        .order_by(Payment.created_at.desc())
    )
    return [
        DashboardPayoutDetailResponse(
            payment_id=payment.id,
            booking_id=booking.id,
            client_name=client.full_name,
            service_name=service.name,
            amount=payment.amount,
            platform_fee_amount=payment.platform_fee_amount,
            business_net_amount=payment.business_net_amount,
            settlement_status=payment.settlement_status,
            payout_attempt_count=getattr(payment, "payout_attempt_count", 0),
            payout_review_reason=getattr(payment, "payout_review_reason", None),
            last_payout_error=getattr(payment, "last_payout_error", None),
            next_payout_attempt_at=getattr(payment, "next_payout_attempt_at", None),
            payout_transfer_reference=payment.payout_transfer_reference,
            payout_transfer_code=payment.payout_transfer_code,
        )
        for payment, booking, client, service in result.all()
    ]


@router.post("/payouts/{payment_id}/approve", response_model=DashboardPayoutResponse)
async def approve_dashboard_payout(
    payment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardPayoutResponse:
    payment = await approve_payout(db, tenant_id=current_user.tenant_id, payment_id=payment_id)
    return DashboardPayoutResponse(
        payment_id=payment.id,
        settlement_status=payment.settlement_status,
        payout_transfer_reference=payment.payout_transfer_reference,
        payout_transfer_code=payment.payout_transfer_code,
    )


@router.post("/payouts/{payment_id}/retry", response_model=DashboardPayoutResponse)
async def retry_dashboard_payout(
    payment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardPayoutResponse:
    payment = await approve_payout(db, tenant_id=current_user.tenant_id, payment_id=payment_id)
    return DashboardPayoutResponse(
        payment_id=payment.id,
        settlement_status=payment.settlement_status,
        payout_transfer_reference=payment.payout_transfer_reference,
        payout_transfer_code=payment.payout_transfer_code,
    )


async def load_inspo_assets(db: AsyncSession, booking_ids: list[UUID]) -> dict[UUID, list[BookingInspoAsset]]:
    if not booking_ids:
        return {}
    result = await db.execute(
        select(BookingInspoAsset).where(BookingInspoAsset.booking_id.in_(booking_ids)).order_by(BookingInspoAsset.created_at)
    )
    assets_by_booking: dict[UUID, list[BookingInspoAsset]] = {booking_id: [] for booking_id in booking_ids}
    if not hasattr(result, "scalars"):
        return assets_by_booking
    for asset in result.scalars().all():
        assets_by_booking.setdefault(asset.booking_id, []).append(asset)
    return assets_by_booking


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyticsOverviewResponse:
    to_dt = datetime.now(UTC)
    from_dt = to_dt - timedelta(days=30)
    count_result = await db.execute(
        select(func.count(Booking.id)).where(Booking.tenant_id == current_user.tenant_id, Booking.created_at >= from_dt)
    )
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.tenant_id == current_user.tenant_id,
            Payment.status == "success",
            Payment.created_at >= from_dt,
        )
    )
    top_result = await db.execute(
        select(Service.name, func.count(Booking.id).label("count"))
        .join(Booking, Booking.service_id == Service.id)
        .where(Booking.tenant_id == current_user.tenant_id, Booking.created_at >= from_dt)
        .group_by(Service.name)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
    )
    return AnalyticsOverviewResponse(
        from_date=from_dt.date(),
        to_date=to_dt.date(),
        bookings_count=count_result.scalar_one(),
        revenue=revenue_result.scalar_one(),
        top_services=[{"name": name, "count": count} for name, count in top_result.all()],
    )
