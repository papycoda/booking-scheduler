from uuid import UUID
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.tenant import Tenant
from app.services.paystack_service import PaystackError, initiate_transfer

PAYOUT_RETRY_DELAYS = (timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))


async def queue_payment_for_payout(db: AsyncSession, *, payment: Payment, tenant: Tenant | None) -> Payment:
    if payment.collection_mode != "platform_collected" or payment.status != "success":
        payment.settlement_status = "not_due"
        return payment
    if tenant is None or not getattr(tenant, "payout_recipient_code", None):
        payment.settlement_status = "needs_setup"
        payment.payout_review_reason = "payout_account_missing"
        return payment

    paid_count_result = await db.execute(
        select(func.count(Payment.id)).where(
            Payment.tenant_id == payment.tenant_id,
            Payment.collection_mode == "platform_collected",
            Payment.settlement_status == "paid",
            Payment.id != payment.id,
        )
    )
    paid_count = paid_count_result.scalar_one()
    if paid_count == 0:
        payment.settlement_status = "needs_review"
        payment.payout_review_reason = "first_payout"
        return payment

    payment.settlement_status = "queued"
    payment.payout_review_reason = None
    payment.next_payout_attempt_at = datetime.now(UTC)
    return payment


async def approve_payout(db: AsyncSession, *, tenant_id: UUID, payment_id: UUID) -> Payment:
    payment = await _load_payment_for_tenant(db, tenant_id=tenant_id, payment_id=payment_id)
    if payment.collection_mode != "platform_collected" or payment.status != "success":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "PAYOUT_NOT_AVAILABLE", "message": "This payment is not ready for payout."})
    if payment.settlement_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "PAYOUT_ALREADY_SENT", "message": "This payout has already been sent."})
    payment.settlement_status = "queued"
    payment.payout_review_reason = None
    payment.next_payout_attempt_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(payment)
    return payment


async def initiate_platform_collected_payout(db: AsyncSession, *, tenant_id: UUID, payment_id: UUID) -> Payment:
    payment = await _load_payment_for_tenant(db, tenant_id=tenant_id, payment_id=payment_id)
    if payment.collection_mode != "platform_collected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "DIRECT_SPLIT_PAYMENT", "message": "This payment was already split at checkout."})
    if payment.status != "success" or payment.settlement_status not in {"queued", "pending", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "PAYOUT_NOT_AVAILABLE", "message": "This payment is not ready for payout."})

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None or not tenant.payout_recipient_code:
        payment.settlement_status = "needs_setup"
        payment.payout_review_reason = "payout_account_missing"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "PAYOUT_SETUP_REQUIRED", "message": "Add payout bank details before sending this payout."})

    reference = payment.payout_transfer_reference or f"payout_{payment.id.hex}"
    payment.payout_transfer_reference = reference
    payment.settlement_status = "processing"
    payment.payout_attempt_count = getattr(payment, "payout_attempt_count", 0) + 1
    payment.last_payout_attempt_at = datetime.now(UTC)
    payment.next_payout_attempt_at = None
    try:
        data = await initiate_transfer(
            amount=payment.business_net_amount,
            recipient=tenant.payout_recipient_code,
            reference=reference,
            reason=f"Booking payout {payment.booking_id}",
        )
    except PaystackError as exc:
        if payment.payout_attempt_count >= len(PAYOUT_RETRY_DELAYS):
            payment.settlement_status = "needs_review"
            payment.payout_review_reason = "retry_limit_reached"
            payment.next_payout_attempt_at = None
        else:
            payment.settlement_status = "failed"
            payment.next_payout_attempt_at = datetime.now(UTC) + PAYOUT_RETRY_DELAYS[payment.payout_attempt_count - 1]
        payment.last_payout_error = str(exc) or "Provider payout failed."
        await db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error": "PAYOUT_FAILED", "message": "Could not initiate provider payout."}) from None

    payment.settlement_status = "paid"
    payment.payout_transfer_code = data.get("transfer_code")
    payment.payout_review_reason = None
    payment.last_payout_error = None
    await db.commit()
    await db.refresh(payment)
    return payment


async def process_due_payouts(db: AsyncSession, *, limit: int = 25) -> int:
    now = datetime.now(UTC)
    result = await db.execute(
        select(Payment)
        .where(
            Payment.status == "success",
            Payment.collection_mode == "platform_collected",
            Payment.settlement_status.in_(("queued", "failed")),
            or_(Payment.next_payout_attempt_at.is_(None), Payment.next_payout_attempt_at <= now),
        )
        .order_by(Payment.created_at)
        .limit(limit)
    )
    count = 0
    for payment in result.scalars().all():
        try:
            await initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)
            count += 1
        except HTTPException:
            continue
    return count


async def _load_payment_for_tenant(db: AsyncSession, *, tenant_id: UUID, payment_id: UUID) -> Payment:
    result = await db.execute(select(Payment).where(Payment.tenant_id == tenant_id, Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "PAYMENT_NOT_FOUND", "message": "Payment was not found."})
    return payment
