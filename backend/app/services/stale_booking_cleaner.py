"""
Background service to clean up stale pending_payment bookings.

Bookings in pending_payment status that exceed the payment timeout are
automatically marked as expired to prevent indefinite slot reservation.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, UTC

from app.models.booking import Booking
from app.models.payment import Payment


logger = logging.getLogger(__name__)


# Configurable timeout for pending payments (default 30 minutes)
PENDING_PAYMENT_TIMEOUT_MINUTES = 30


async def expire_stale_pending_bookings(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    timeout_minutes: int = PENDING_PAYMENT_TIMEOUT_MINUTES,
) -> int:
    """
    Expire bookings that have been in pending_payment status for too long.

    This prevents indefinite slot reservation when users abandon the
    payment flow. Bookings older than the timeout are marked as 'expired'
    and their associated payments are marked as 'expired'.

    Args:
        db: Database session
        now: Current time for testing (defaults to datetime.now(UTC))
        timeout_minutes: Minutes after which a pending booking is considered stale

    Returns:
        Number of bookings expired
    """
    if now is None:
        now = datetime.now(UTC)

    cutoff = now - timedelta(minutes=timeout_minutes)

    # Find all bookings in pending_payment that are older than the cutoff
    # We need to check if they have an associated payment record
    result = await db.execute(
        select(Booking, Payment)
        .join(Payment, Payment.booking_id == Booking.id)
        .where(
            Booking.status == "pending_payment",
            Payment.status == "pending",
            Booking.created_at <= cutoff,
        )
    )

    bookings_to_expire = result.all()
    count = len(bookings_to_expire)

    if count == 0:
        return 0

    logger.info(
        "Expiring %d stale pending_payment bookings (older than %s)",
        count,
        cutoff.isoformat(),
    )

    for booking, payment in bookings_to_expire:
        booking.status = "expired"
        booking.updated_at = now
        payment.status = "expired"

    await db.commit()

    logger.info("Expired %d stale pending_payment bookings", count)
    return count
