from typing import Any

import httpx

from app.config import settings


class PaystackError(Exception):
    pass


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
    headers = {"Authorization": f"Bearer {settings.paystack_secret_key}"}
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
    subaccount: str,
    transaction_charge: int,
    callback_url: str,
    metadata: dict[str, str],
) -> dict[str, Any]:
    payload = {
        "email": email,
        "amount": amount,
        "reference": reference,
        "subaccount": subaccount,
        "bearer": "subaccount",
        "transaction_charge": transaction_charge,
        "callback_url": callback_url,
        "metadata": metadata,
    }
    headers = {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
        "X-Idempotency-Key": reference,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
    if response.status_code >= 400:
        raise PaystackError("Paystack transaction initialization failed.")
    body = response.json()
    if not body.get("status") or "data" not in body:
        raise PaystackError("Paystack returned an unexpected transaction response.")
    return body["data"]
