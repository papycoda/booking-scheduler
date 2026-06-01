from dataclasses import dataclass
from decimal import Decimal

from app.models.tenant import Tenant
from app.services.paystack_service import initialize_transaction

MAX_PLATFORM_FEE_PERCENT = Decimal("10.00")


@dataclass(frozen=True)
class PaymentPlan:
    provider: str
    collection_mode: str
    platform_fee_amount: int
    business_net_amount: int
    subaccount: str | None
    transaction_charge: int
    bearer: str | None


def capped_platform_fee_percentage(tenant: Tenant) -> Decimal:
    configured = Decimal(str(getattr(tenant, "platform_fee_percentage", 0) or 0))
    return min(configured, MAX_PLATFORM_FEE_PERCENT)


def build_payment_plan(tenant: Tenant, amount: int) -> PaymentPlan:
    platform_fee = int((Decimal(amount) * capped_platform_fee_percentage(tenant)) / Decimal("100"))
    business_net = max(amount - platform_fee, 0)
    subaccount = getattr(tenant, "paystack_subaccount_code", None)
    if getattr(tenant, "payment_setup_status", None) == "split_ready" and subaccount:
        return PaymentPlan(
            provider="paystack",
            collection_mode="direct_split",
            platform_fee_amount=platform_fee,
            business_net_amount=business_net,
            subaccount=subaccount,
            transaction_charge=platform_fee,
            bearer="subaccount",
        )
    return PaymentPlan(
        provider="paystack",
        collection_mode="platform_collected",
        platform_fee_amount=platform_fee,
        business_net_amount=business_net,
        subaccount=None,
        transaction_charge=0,
        bearer=None,
    )


async def initialize_checkout_payment(
    *,
    email: str,
    amount: int,
    reference: str,
    tenant: Tenant,
    callback_url: str,
    metadata: dict[str, str],
) -> tuple[dict, PaymentPlan]:
    plan = build_payment_plan(tenant, amount)
    data = await initialize_transaction(
        email=email,
        amount=amount,
        reference=reference,
        subaccount=plan.subaccount,
        transaction_charge=plan.transaction_charge,
        bearer=plan.bearer,
        callback_url=callback_url,
        metadata={
            **metadata,
            "provider": plan.provider,
            "collection_mode": plan.collection_mode,
            "platform_fee_amount": str(plan.platform_fee_amount),
            "business_net_amount": str(plan.business_net_amount),
        },
    )
    return data, plan
