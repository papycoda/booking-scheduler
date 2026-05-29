import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.services.notification_service import process_due_reminders

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_reminder_job() -> None:
    async with SessionLocal() as db:
        count = await process_due_reminders(db)
        logger.info("Processed booking reminders: %s", count)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(run_reminder_job, "interval", minutes=15, id="booking-reminders", replace_existing=True)
    scheduler.start()
