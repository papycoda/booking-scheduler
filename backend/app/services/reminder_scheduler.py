import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.services.notification_service import process_due_reminders
from app.services.payment_lifecycle_service import expire_unpaid_bookings
from app.services.settlement_service import process_due_payouts
from app.services.stale_booking_cleaner import expire_stale_pending_bookings
from app.services.whatsapp_service import retry_pending_payment_initializations

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_reminder_job() -> None:
    async with SessionLocal() as db:
        count = await process_due_reminders(db)
        logger.info("Processed booking reminders: %s", count)


async def run_payment_lifecycle_job() -> None:
    from datetime import UTC, datetime

    async with SessionLocal() as db:
        expired_count = await expire_unpaid_bookings(db, now=datetime.now(UTC), hold_minutes=15)
        payout_count = await process_due_payouts(db)
        logger.info("Processed payment lifecycle: expired=%s payouts=%s", expired_count, payout_count)


async def run_stale_booking_cleanup_job() -> None:
    """Background job to expire stale pending_payment bookings."""
    async with SessionLocal() as db:
        count = await expire_stale_pending_bookings(db)
        if count > 0:
            logger.info("Stale booking cleanup: expired %d pending_payment bookings", count)


async def run_whatsapp_retry_job() -> None:
    async with SessionLocal() as db:
        count = await retry_pending_payment_initializations(db)
        if count > 0:
            logger.info("WhatsApp payment-link retry: initialized %d payment links", count)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(run_reminder_job, "interval", minutes=15, id="booking-reminders", replace_existing=True)
    scheduler.add_job(run_payment_lifecycle_job, "interval", minutes=5, id="payment-lifecycle", replace_existing=True)
    scheduler.add_job(run_stale_booking_cleanup_job, "interval", minutes=5, id="stale-booking-cleanup", replace_existing=True)
    scheduler.add_job(run_whatsapp_retry_job, "interval", minutes=3, id="whatsapp-payment-retry", replace_existing=True)
    scheduler.start()
