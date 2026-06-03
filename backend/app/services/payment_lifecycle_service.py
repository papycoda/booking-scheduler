from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.payment import Payment


async def expire_unpaid_bookings(db: AsyncSession, *, now: datetime, hold_minutes: int = 15) -> int:
    cutoff = now - timedelta(minutes=hold_minutes)
    result = await db.execute(
        select(Booking, Payment)
        .join(Payment, Payment.booking_id == Booking.id)
        .where(
            Booking.status == "pending_payment",
            Payment.status == "pending",
            Booking.created_at <= cutoff,
        )
    )
    count = 0
    for booking, payment in result.all():
        booking.status = "expired"
        payment.status = "expired"
        count += 1
    if count:
        await db.commit()
    return count
