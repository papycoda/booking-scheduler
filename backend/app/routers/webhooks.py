import hashlib
import hmac
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, Request, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.tenant import Tenant
from app.services.notification_service import send_booking_confirmation
from app.services.payment_provider import DEMO_ACCESS_CODE_PREFIX, verify_demo_payment_token
from app.services.settlement_service import queue_payment_for_payout

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/demo/complete-payment")
async def demo_complete_payment(
    reference: str,
    background_tasks: BackgroundTasks,
    token: str | None = None,
) -> JSONResponse:
    """
    Demo endpoint to simulate a successful Paystack payment completion.
    Only works when DEMO_MODE=true.
    """
    if not settings.demo_mode:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"status": "demo_mode_disabled", "message": "Demo mode is not enabled"}
        )
    if not verify_demo_payment_token(reference, token):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"status": "invalid_demo_token", "message": "Demo payment token is invalid."},
        )

    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Payment).where(Payment.paystack_reference == reference))
            payment = result.scalar_one_or_none()
            if payment is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"status": "payment_not_found", "message": f"No payment found with reference {reference}"}
                )
            if not str(payment.paystack_access_code or "").startswith(DEMO_ACCESS_CODE_PREFIX):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"status": "not_demo_payment", "message": "Only demo payments can be completed here."},
                )
            if payment.status == "success":
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "already_paid"})

            booking_result = await db.execute(select(Booking).where(Booking.id == payment.booking_id))
            booking = booking_result.scalar_one_or_none()
            if booking is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"status": "booking_not_found", "message": f"No booking found for payment {payment.id}"}
                )

            # Simulate successful payment
            payment.status = "success"
            payment.metadata_ = {"event": "charge.success", "demo": True}
            from datetime import UTC, datetime
            payment.paid_at = datetime.now(UTC)

            if getattr(payment, "collection_mode", "platform_collected") == "platform_collected":
                tenant_result = await db.execute(select(Tenant).where(Tenant.id == payment.tenant_id))
                await queue_payment_for_payout(db, payment=payment, tenant=tenant_result.scalar_one_or_none())

            booking.status = "confirmed"
            await db.commit()
            background_tasks.add_task(send_booking_confirmation_for_booking, booking.id)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "success",
                    "message": "Demo payment completed successfully",
                    "payment_id": str(payment.id),
                    "booking_id": str(booking.id),
                }
            )
    except Exception as e:
        logger.exception("Demo payment completion failed: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(e)}
        )


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
            if not verify_paystack_charge_success(event, payment):
                logger.error("Paystack charge.success verification failed for reference %s", reference)
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored"})

            booking_result = await db.execute(select(Booking).where(Booking.id == payment.booking_id))
            booking = booking_result.scalar_one_or_none()
            if booking is None:
                logger.error("Payment %s has no booking", payment.id)
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})

            # Fix 3: Prevent expired bookings from being resurrected by late webhooks
            if payment.status == "expired" or booking.status == "expired":
                logger.warning("Ignoring webhook for expired payment %s / booking %s", payment.id, booking.id)
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ignored_expired"})

            payment.status = "success"
            payment.metadata_ = event
            from datetime import UTC, datetime

            payment.paid_at = datetime.now(UTC)
            if getattr(payment, "collection_mode", "platform_collected") == "platform_collected":
                tenant_result = await db.execute(select(Tenant).where(Tenant.id == payment.tenant_id))
                await queue_payment_for_payout(db, payment=payment, tenant=tenant_result.scalar_one_or_none())
            booking.status = "confirmed"
            await db.commit()
            background_tasks.add_task(send_booking_confirmation_for_booking, booking.id)
    except Exception:
        logger.exception("Paystack webhook processing failed")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "error_logged"})

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})


def verify_paystack_charge_success(event: dict, payment: Payment) -> bool:
    data = event.get("data") or {}
    try:
        amount = int(data.get("amount"))
    except (TypeError, ValueError):
        return False
    currency = str(data.get("currency") or "").upper()
    reference = str(data.get("reference") or "").strip()
    return reference == payment.paystack_reference and amount == payment.amount and currency == payment.currency.upper()


async def send_booking_confirmation_for_booking(booking_id: UUID) -> None:
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Booking).where(Booking.id == booking_id))
            booking = result.scalar_one_or_none()
            if booking is not None:
                await send_booking_confirmation(db, booking)
    except Exception:
        logger.exception("Paystack confirmation notification failed")
