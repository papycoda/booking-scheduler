from app.models.service import Service
from app.models.tenant import Tenant


def calculate_deposit_due_now(tenant: Tenant, service: Service) -> int:
    deposit_policy = getattr(service, "deposit_policy", "tenant_default")
    pricing_mode = getattr(service, "pricing_mode", "fixed")
    if deposit_policy == "custom":
        return int(getattr(service, "deposit_amount", 0) or 0)
    if deposit_policy == "tenant_default":
        default_deposit = int(getattr(tenant, "default_deposit_amount", 0) or 0)
        if default_deposit > 0:
            return default_deposit
        if pricing_mode == "fixed":
            return int(service.price)
        return 0
    if pricing_mode == "fixed":
        return int(service.price)
    return 0


def requires_deposit_for_booking(service: Service) -> bool:
    return getattr(service, "pricing_mode", "fixed") in {"from", "consultation"} or getattr(service, "deposit_policy", "tenant_default") != "disabled"


def price_status_for_service(service: Service) -> str:
    if getattr(service, "pricing_mode", "fixed") == "fixed":
        return "fixed"
    return "pending_quote"


def payment_type_for_service(service: Service) -> str:
    if getattr(service, "deposit_policy", "tenant_default") == "disabled" and getattr(service, "pricing_mode", "fixed") == "fixed":
        return "full"
    return "deposit"


def price_label_for_service(service: Service) -> str:
    if service.pricing_mode == "consultation":
        return "Price by consultation"
    if service.pricing_mode == "from":
        return f"From {service.currency} {service.price}"
    return f"{service.currency} {service.price}"
