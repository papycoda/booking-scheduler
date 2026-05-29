import os
import unittest

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.services import paystack_service as svc  # noqa: E402


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/test",
                "access_code": "access_test",
            },
        }


class FakeAsyncClient:
    calls = []

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
        return FakeResponse()


class PaystackServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_client = svc.httpx.AsyncClient
        FakeAsyncClient.calls = []
        svc.httpx.AsyncClient = FakeAsyncClient

    def tearDown(self) -> None:
        svc.httpx.AsyncClient = self.original_client

    async def test_initialize_transaction_sends_split_payload_and_idempotency_header(self):
        data = await svc.initialize_transaction(
            email="chioma@example.com",
            amount=10_000,
            reference="bk_reference",
            subaccount="ACCT_test",
            transaction_charge=500,
            callback_url="http://localhost:3000/book/ada/verify?booking_id=123",
            metadata={"booking_id": "123"},
        )

        self.assertEqual(data["authorization_url"], "https://checkout.paystack.com/test")
        call = FakeAsyncClient.calls[0]
        self.assertEqual(call["url"], "https://api.paystack.co/transaction/initialize")
        self.assertEqual(call["json"]["bearer"], "subaccount")
        self.assertEqual(call["json"]["transaction_charge"], 500)
        self.assertEqual(call["json"]["subaccount"], "ACCT_test")
        self.assertEqual(call["headers"]["X-Idempotency-Key"], "bk_reference")
        self.assertEqual(call["headers"]["Authorization"], "Bearer sk_test_x")
