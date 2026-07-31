from typing import Any

import httpx

from app.config import settings


class PaystackError(Exception):
    pass


class PaystackNotConfiguredError(PaystackError):
    pass


def paystack_headers(*, idempotency_key: str | None = None) -> dict[str, str]:
    secret_key = settings.paystack_secret_key.strip()
    if not secret_key:
        raise PaystackNotConfiguredError("Paystack secret key is not configured.")
    headers = {"Authorization": f"Bearer {secret_key}"}
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    return headers


async def create_subaccount(
    *,
    business_name: str,
    settlement_bank: str,
    account_number: str,
    percentage_charge: float,
) -> dict[str, Any]:
    payload = {
        "business_name": business_name,
        "settlement_bank": settlement_bank,
        "account_number": account_number,
        "percentage_charge": percentage_charge,
    }
    headers = paystack_headers()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post("https://api.paystack.co/subaccount", json=payload, headers=headers)
    if response.status_code >= 400:
        raise PaystackError("Paystack subaccount creation failed.")
    body = response.json()
    if not body.get("status") or "data" not in body:
        raise PaystackError("Paystack returned an unexpected subaccount response.")
    return body["data"]


async def initialize_transaction(
    *,
    email: str,
    amount: int,
    reference: str,
    subaccount: str | None,
    transaction_charge: int,
    bearer: str | None = None,
    callback_url: str,
    metadata: dict[str, str],
) -> dict[str, Any]:
    payload = {
        "email": email,
        "amount": amount,
        "reference": reference,
        "callback_url": callback_url,
        "metadata": metadata,
    }
    if subaccount:
        payload["subaccount"] = subaccount
    if bearer or (subaccount and transaction_charge):
        payload["bearer"] = bearer or "subaccount"
    if transaction_charge:
        payload["transaction_charge"] = transaction_charge
    headers = paystack_headers(idempotency_key=reference)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
    if response.status_code >= 400:
        raise PaystackError("Paystack transaction initialization failed.")
    body = response.json()
    if not body.get("status") or "data" not in body:
        raise PaystackError("Paystack returned an unexpected transaction response.")
    return body["data"]


async def create_transfer_recipient(
    *,
    name: str,
    account_number: str,
    bank_code: str,
    currency: str = "NGN",
) -> dict[str, Any]:
    payload = {
        "type": "nuban",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": currency,
    }
    headers = paystack_headers()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post("https://api.paystack.co/transferrecipient", json=payload, headers=headers)
    if response.status_code >= 400:
        raise PaystackError("Paystack transfer recipient creation failed.")
    body = response.json()
    if not body.get("status") or "data" not in body:
        raise PaystackError("Paystack returned an unexpected transfer recipient response.")
    return body["data"]


async def list_banks(*, country: str = "nigeria") -> list[dict[str, Any]]:
    headers = paystack_headers()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"https://api.paystack.co/bank?country={country}", headers=headers)
    if response.status_code >= 400:
        raise PaystackError("Paystack bank lookup failed.")
    body = response.json()
    if not body.get("status") or "data" not in body:
        raise PaystackError("Paystack returned an unexpected bank lookup response.")
    return body["data"]


async def resolve_bank_code(bank_name_or_code: str) -> tuple[str, str]:
    value = bank_name_or_code.strip()
    if value.isdigit():
        return value, value
    normalized = value.lower()
    for bank in await list_banks():
        name = str(bank.get("name") or "")
        code = str(bank.get("code") or "")
        slug = str(bank.get("slug") or "")
        aliases = {name.lower(), code.lower(), slug.lower()}
        if normalized in aliases or normalized in name.lower():
            return code, name
    raise PaystackError("Bank was not found.")


async def initiate_transfer(
    *,
    amount: int,
    recipient: str,
    reference: str,
    reason: str,
    currency: str = "NGN",
) -> dict[str, Any]:
    payload = {
        "source": "balance",
        "amount": amount,
        "recipient": recipient,
        "reference": reference,
        "reason": reason,
        "currency": currency,
    }
    headers = paystack_headers()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.paystack.co/transfer", json=payload, headers=headers)
    if response.status_code >= 400:
        raise PaystackError("Paystack transfer failed.")
    body = response.json()
    if not body.get("status") or "data" not in body:
        raise PaystackError("Paystack returned an unexpected transfer response.")
    return body["data"]
