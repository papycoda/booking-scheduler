import os
import unittest
from types import SimpleNamespace
from uuid import uuid4
from datetime import UTC, datetime, timedelta

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.services import settlement_service as svc  # noqa: E402


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, payment, tenant):
        self.payment = payment
        self.tenant = tenant
        self.calls = 0
        self.committed = False
        self.refreshed = None

    async def execute(self, _stmt):
        self.calls += 1
        return FakeResult(self.payment if self.calls == 1 else self.tenant)

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed = item


class FakeCountResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeQueueSession:
    def __init__(self, paid_count):
        self.paid_count = paid_count

    async def execute(self, _stmt):
        return FakeCountResult(self.paid_count)


class SettlementServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_initiate_transfer = svc.initiate_transfer

    def tearDown(self) -> None:
        svc.initiate_transfer = self.original_initiate_transfer

    async def test_initiate_platform_collected_payout_marks_payment_paid(self):
        tenant_id = uuid4()
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant_id,
            booking_id=uuid4(),
            collection_mode="platform_collected",
            status="success",
            settlement_status="pending",
            business_net_amount=9_500,
            payout_transfer_reference=None,
            payout_transfer_code=None,
        )
        tenant = SimpleNamespace(id=tenant_id, payout_recipient_code="RCP_test")
        captured = {}

        async def initiate_transfer(**kwargs):
            captured.update(kwargs)
            return {"transfer_code": "TRF_test"}

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        result = await svc.initiate_platform_collected_payout(db, tenant_id=tenant_id, payment_id=payment.id)

        self.assertIs(result, payment)
        self.assertTrue(db.committed)
        self.assertIs(db.refreshed, payment)
        self.assertEqual(captured["amount"], 9_500)
        self.assertEqual(captured["recipient"], "RCP_test")
        self.assertEqual(payment.settlement_status, "paid")
        self.assertEqual(payment.payout_transfer_code, "TRF_test")

    async def test_queue_payment_for_payout_requires_review_for_first_business_payout(self):
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            status="success",
            collection_mode="platform_collected",
            settlement_status="not_due",
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(payout_recipient_code="RCP_test")

        await svc.queue_payment_for_payout(FakeQueueSession(paid_count=0), payment=payment, tenant=tenant)

        self.assertEqual(payment.settlement_status, "needs_review")
        self.assertEqual(payment.payout_review_reason, "first_payout")

    async def test_queue_payment_for_payout_queues_repeat_business_payout(self):
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            status="success",
            collection_mode="platform_collected",
            settlement_status="not_due",
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(payout_recipient_code="RCP_test")

        await svc.queue_payment_for_payout(FakeQueueSession(paid_count=1), payment=payment, tenant=tenant)

        self.assertEqual(payment.settlement_status, "queued")
        self.assertIsNone(payment.payout_review_reason)

    async def test_approve_payout_moves_reviewed_payment_to_queue(self):
        tenant_id = uuid4()
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant_id,
            collection_mode="platform_collected",
            status="success",
            settlement_status="needs_review",
            payout_review_reason="first_payout",
            next_payout_attempt_at=None,
        )
        db = FakeSession(payment, None)

        result = await svc.approve_payout(db, tenant_id=tenant_id, payment_id=payment.id)

        self.assertIs(result, payment)
        self.assertEqual(payment.settlement_status, "queued")
        self.assertIsNone(payment.payout_review_reason)
        self.assertIsNotNone(payment.next_payout_attempt_at)
        self.assertTrue(db.committed)

    async def test_failed_payout_retries_three_times_then_needs_review(self):
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            booking_id=uuid4(),
            collection_mode="platform_collected",
            status="success",
            settlement_status="queued",
            business_net_amount=9_500,
            payout_transfer_reference=None,
            payout_transfer_code=None,
            payout_attempt_count=2,
            last_payout_attempt_at=None,
            next_payout_attempt_at=datetime.now(UTC) - timedelta(minutes=1),
            last_payout_error=None,
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code="RCP_test")

        async def initiate_transfer(**_kwargs):
            raise svc.PaystackError("provider down")

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        with self.assertRaises(Exception):
            await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        self.assertEqual(payment.payout_attempt_count, 3)
        self.assertEqual(payment.settlement_status, "needs_review")
        self.assertEqual(payment.payout_review_reason, "retry_limit_reached")
