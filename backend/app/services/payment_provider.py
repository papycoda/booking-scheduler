from dataclasses import dataclass
from decimal import Decimal
import hashlib
import hmac
from urllib.parse import urlencode

from app.config import settings
from app.models.tenant import Tenant
from app.services.paystack_service import initialize_transaction

MAX_PLATFORM_FEE_PERCENT = Decimal("10.00")
MAX_PLATFORM_FEE_AMOUNT = 500_000
DEMO_ACCESS_CODE_PREFIX = "demo_access_"


@dataclass(frozen=True)
class PaymentPlan:
    provider: str
    collection_mode: str
    platform_fee_amount: int
    business_net_amount: int
    subaccount: str | None
    transaction_charge: int
    bearer: str | None


def _demo_transaction_response(reference: str, callback_url: str, metadata: dict[str, str]) -> dict:
    """Returns mock Paystack transaction response for demo mode."""
    query = urlencode({"reference": reference, "token": signed_demo_payment_token(reference)})
    return {
        "authorization_url": f"{str(settings.frontend_url).rstrip('/')}/demo/pay?{query}",
        "access_code": f"{DEMO_ACCESS_CODE_PREFIX}{reference[:8]}",
        "reference": reference,
        "metadata": metadata,
    }


def signed_demo_payment_token(reference: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        f"demo-payment:{reference}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_demo_payment_token(reference: str, token: str | None) -> bool:
    if not reference or not token:
        return False
    return hmac.compare_digest(token, signed_demo_payment_token(reference))


def is_demo_admin(email: str) -> bool:
    """Check if the given email is authorized for demo mode payments."""
    if not settings.demo_mode or not settings.demo_admin_emails:
        return False
    normalized_email = email.strip().lower()
    return normalized_email in settings.demo_admin_emails_list


def capped_platform_fee_percentage(tenant: Tenant) -> Decimal:
    configured = Decimal(str(getattr(tenant, "platform_fee_percentage", 0) or 0))
    return min(configured, MAX_PLATFORM_FEE_PERCENT)


def build_payment_plan(tenant: Tenant, amount: int) -> PaymentPlan:
    platform_fee = min(int((Decimal(amount) * capped_platform_fee_percentage(tenant)) / Decimal("100")), MAX_PLATFORM_FEE_AMOUNT)
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

    # Demo mode is only available to authorized admin emails
    if settings.demo_mode and is_demo_admin(email):
        extended_metadata = {
            **metadata,
            "provider": plan.provider,
            "collection_mode": plan.collection_mode,
            "platform_fee_amount": str(plan.platform_fee_amount),
            "business_net_amount": str(plan.business_net_amount),
        }
        data = _demo_transaction_response(reference, callback_url, extended_metadata)
        return data, plan

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
