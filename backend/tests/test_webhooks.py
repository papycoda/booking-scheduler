import hashlib
import hmac
import json
import os
import unittest
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from fastapi import BackgroundTasks  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import webhooks  # noqa: E402


class FakeRequest:
    def __init__(self, body: bytes, payload: dict):
        self._body = body
        self._payload = payload

    async def body(self):
        return self._body

    async def json(self):
        return self._payload


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeWebhookSession:
    def __init__(self, payment, booking):
        self.payment = payment
        self.booking = booking
        self.committed = False
        self.execute_count = 0

    async def execute(self, _stmt):
        self.execute_count += 1
        if self.execute_count == 1:
            return FakeScalarResult(self.payment)
        return FakeScalarResult(self.booking)

    async def commit(self):
        self.committed = True


class FakeSessionFactory:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class PaystackWebhookTests(unittest.TestCase):
    def setUp(self):
        self.original_session_local = webhooks.SessionLocal

    def tearDown(self):
        webhooks.SessionLocal = self.original_session_local

    def test_invalid_signature_returns_400_before_processing(self):
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/webhooks/paystack",
                content=b'{"event":"charge.success"}',
                headers={"x-paystack-signature": "invalid"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"status": "invalid_signature"})

    def test_non_charge_success_event_with_valid_signature_is_ignored(self):
        body = json.dumps({"event": "transfer.success", "data": {"reference": "ref"}}).encode("utf-8")
        signature = hmac.new(settings.paystack_secret_key.encode("utf-8"), body, hashlib.sha512).hexdigest()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/webhooks/paystack",
                content=body,
                headers={"x-paystack-signature": signature, "content-type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ignored"})

    def test_charge_success_updates_payment_booking_and_queues_notification(self):
        booking_id = uuid4()
        payment = SimpleNamespace(id=uuid4(), booking_id=booking_id, status="pending", metadata_=None, paid_at=None)
        booking = SimpleNamespace(id=booking_id, status="pending_payment")
        session = FakeWebhookSession(payment, booking)
        webhooks.SessionLocal = lambda: FakeSessionFactory(session)
        event = {"event": "charge.success", "data": {"reference": "bk_reference"}}
        body = json.dumps(event).encode("utf-8")
        signature = hmac.new(settings.paystack_secret_key.encode("utf-8"), body, hashlib.sha512).hexdigest()
        background_tasks = BackgroundTasks()

        response = __import__("asyncio").run(
            webhooks.paystack_webhook(
                FakeRequest(body, event),
                background_tasks,
                x_paystack_signature=signature,
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(session.committed)
        self.assertEqual(payment.status, "success")
        self.assertEqual(payment.metadata_, event)
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(booking.status, "confirmed")
        self.assertEqual(len(background_tasks.tasks), 1)
