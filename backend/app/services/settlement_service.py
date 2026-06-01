from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.tenant import Tenant
from app.services.paystack_service import PaystackError, initiate_transfer


async def initiate_platform_collected_payout(db: AsyncSession, *, tenant_id: UUID, payment_id: UUID) -> Payment:
    result = await db.execute(select(Payment).where(Payment.tenant_id == tenant_id, Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "PAYMENT_NOT_FOUND", "message": "Payment was not found."})
    if payment.collection_mode != "platform_collected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "DIRECT_SPLIT_PAYMENT", "message": "This payment was already split at checkout."})
    if payment.status != "success" or payment.settlement_status not in {"pending", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "PAYOUT_NOT_AVAILABLE", "message": "This payment is not ready for payout."})

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None or not tenant.payout_recipient_code:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "PAYOUT_SETUP_REQUIRED", "message": "Add payout bank details before sending this payout."})

    reference = payment.payout_transfer_reference or f"payout_{payment.id.hex}"
    payment.payout_transfer_reference = reference
    try:
        data = await initiate_transfer(
            amount=payment.business_net_amount,
            recipient=tenant.payout_recipient_code,
            reference=reference,
            reason=f"Booking payout {payment.booking_id}",
        )
    except PaystackError:
        payment.settlement_status = "failed"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error": "PAYOUT_FAILED", "message": "Could not initiate provider payout."}) from None

    payment.settlement_status = "paid"
    payment.payout_transfer_code = data.get("transfer_code")
    await db.commit()
    await db.refresh(payment)
    return payment
