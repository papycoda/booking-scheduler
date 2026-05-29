from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.booking import Booking, BookingInspoAsset, Client
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff
from app.models.user import User
from app.schemas.dashboard import AnalyticsOverviewResponse, DashboardBookingResponse, DashboardBookingStatusUpdate

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def booking_row_to_response(row, assets_by_booking: dict[UUID, list[BookingInspoAsset]] | None = None) -> DashboardBookingResponse:
    booking, client, service, staff, payment = row
    assets = assets_by_booking.get(booking.id, []) if assets_by_booking else []
    return DashboardBookingResponse(
        id=booking.id,
        status=booking.status,
        start_time=booking.start_time,
        end_time=booking.end_time,
        client_name=client.full_name,
        client_email=client.email,
        service_name=service.name,
        staff_name=staff.name,
        amount=payment.amount if payment else None,
        payment_status=payment.status if payment else None,
        deposit_amount=getattr(booking, "deposit_amount", payment.amount if payment else 0),
        price_status=getattr(booking, "price_status", "fixed"),
        quoted_price=getattr(booking, "quoted_price", None),
        client_notes=getattr(booking, "client_notes", None),
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
