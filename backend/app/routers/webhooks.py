import hashlib
import hmac
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.notification_service import send_booking_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_paystack_signature: str | None = Header(default=None),
) -> JSONResponse:
    raw_body = await request.body()
    expected_signature = hmac.new(settings.paystack_secret_key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    if not x_paystack_signature or not hmac.compare_digest(x_paystack_signature, expected_signature):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "invalid_signature"})

    try:
        event = await request.json()
    except ValueError:
        logger.exception("Invalid Paystack webhook JSON")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

    logger.info("Paystack webhook received: %s", event.get("event"))
    if event.get("event") != "charge.success":
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

    reference = ((event.get("data") or {}).get("reference") or "").strip()
    if not reference:
        logger.error("Paystack charge.success missing reference")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Payment).where(Payment.paystack_reference == reference))
            payment = result.scalar_one_or_none()
            if payment is None or payment.status == "success":
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})

            booking_result = await db.execute(select(Booking).where(Booking.id == payment.booking_id))
            booking = booking_result.scalar_one_or_none()
            if booking is None:
                logger.error("Payment %s has no booking", payment.id)
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})

            payment.status = "success"
            payment.metadata_ = event
            from datetime import UTC, datetime

            payment.paid_at = datetime.now(UTC)
            booking.status = "confirmed"
            await db.commit()
            background_tasks.add_task(send_booking_confirmation_for_booking, booking.id)
    except Exception:
        logger.exception("Paystack webhook processing failed")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "error_logged"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})


async def send_booking_confirmation_for_booking(booking_id: UUID) -> None:
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Booking).where(Booking.id == booking_id))
            booking = result.scalar_one_or_none()
            if booking is not None:
                await send_booking_confirmation(db, booking)
    except Exception:
        logger.exception("Paystack confirmation notification failed")
