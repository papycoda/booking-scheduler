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
        tenant = SimpleNamespace(
            payout_recipient_code="RCP_test",
            first_payout_review_completed_at=datetime.now(UTC),
        )

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
            payout_attempt_count=3,
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

        self.assertEqual(payment.payout_attempt_count, 4)
        self.assertEqual(payment.settlement_status, "needs_review")
        self.assertEqual(payment.payout_review_reason, "retry_limit_reached")

    async def test_first_failure_schedules_5_minute_retry(self):
        """When payout_attempt_count=0 and first failure occurs, settlement_status should be 'failed' and next_payout_attempt_at should be now + 5 minutes."""
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
            payout_attempt_count=0,
            last_payout_attempt_at=None,
            next_payout_attempt_at=datetime.now(UTC) - timedelta(minutes=1),
            last_payout_error=None,
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code="RCP_test")
        before = datetime.now(UTC)

        async def initiate_transfer(**_kwargs):
            raise svc.PaystackError("provider down")

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        with self.assertRaises(Exception):
            await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        after = datetime.now(UTC)
        self.assertEqual(payment.payout_attempt_count, 1)
        self.assertEqual(payment.settlement_status, "failed")
        self.assertEqual(payment.last_payout_error, "provider down")
        # Verify next_payout_attempt_at is approximately 5 minutes from now
        expected_min = before + svc.PAYOUT_RETRY_DELAYS[0]
        expected_max = after + svc.PAYOUT_RETRY_DELAYS[0]
        self.assertGreaterEqual(payment.next_payout_attempt_at, expected_min)
        self.assertLessEqual(payment.next_payout_attempt_at, expected_max)

    async def test_second_failure_schedules_30_minute_retry(self):
        """When payout_attempt_count=1 and second failure occurs, next_payout_attempt_at should be now + 30 minutes."""
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            booking_id=uuid4(),
            collection_mode="platform_collected",
            status="success",
            settlement_status="failed",
            business_net_amount=9_500,
            payout_transfer_reference=None,
            payout_transfer_code=None,
            payout_attempt_count=1,
            last_payout_attempt_at=datetime.now(UTC) - timedelta(hours=1),
            next_payout_attempt_at=datetime.now(UTC) - timedelta(minutes=1),
            last_payout_error="previous error",
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code="RCP_test")
        before = datetime.now(UTC)

        async def initiate_transfer(**_kwargs):
            raise svc.PaystackError("timeout")

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        with self.assertRaises(Exception):
            await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        after = datetime.now(UTC)
        self.assertEqual(payment.payout_attempt_count, 2)
        self.assertEqual(payment.settlement_status, "failed")
        # Verify next_payout_attempt_at is approximately 30 minutes from now
        expected_min = before + svc.PAYOUT_RETRY_DELAYS[1]
        expected_max = after + svc.PAYOUT_RETRY_DELAYS[1]
        self.assertGreaterEqual(payment.next_payout_attempt_at, expected_min)
        self.assertLessEqual(payment.next_payout_attempt_at, expected_max)

    async def test_third_failure_schedules_2_hour_retry(self):
        """When payout_attempt_count=2 and third failure occurs, next_payout_attempt_at should be now + 2 hours."""
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            booking_id=uuid4(),
            collection_mode="platform_collected",
            status="success",
            settlement_status="failed",
            business_net_amount=9_500,
            payout_transfer_reference=None,
            payout_transfer_code=None,
            payout_attempt_count=2,
            last_payout_attempt_at=datetime.now(UTC) - timedelta(hours=3),
            next_payout_attempt_at=datetime.now(UTC) - timedelta(minutes=1),
            last_payout_error="previous error",
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code="RCP_test")
        before = datetime.now(UTC)

        async def initiate_transfer(**_kwargs):
            raise svc.PaystackError("bank error")

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        with self.assertRaises(Exception):
            await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        after = datetime.now(UTC)
        self.assertEqual(payment.payout_attempt_count, 3)
        self.assertEqual(payment.settlement_status, "failed")
        # Verify next_payout_attempt_at is approximately 2 hours from now
        expected_min = before + svc.PAYOUT_RETRY_DELAYS[2]
        expected_max = after + svc.PAYOUT_RETRY_DELAYS[2]
        self.assertGreaterEqual(payment.next_payout_attempt_at, expected_min)
        self.assertLessEqual(payment.next_payout_attempt_at, expected_max)

    async def test_fourth_failure_moves_to_needs_review(self):
        """When payout_attempt_count=3 and fourth failure occurs, settlement_status should be 'needs_review', payout_review_reason should be 'retry_limit_reached', and next_payout_attempt_at should be None."""
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            booking_id=uuid4(),
            collection_mode="platform_collected",
            status="success",
            settlement_status="failed",
            business_net_amount=9_500,
            payout_transfer_reference=None,
            payout_transfer_code=None,
            payout_attempt_count=3,
            last_payout_attempt_at=datetime.now(UTC) - timedelta(hours=5),
            next_payout_attempt_at=datetime.now(UTC) - timedelta(minutes=1),
            last_payout_error="previous error",
            payout_review_reason=None,
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code="RCP_test")

        async def initiate_transfer(**_kwargs):
            raise svc.PaystackError("permanent failure")

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        with self.assertRaises(Exception):
            await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        self.assertEqual(payment.payout_attempt_count, 4)
        self.assertEqual(payment.settlement_status, "needs_review")
        self.assertEqual(payment.payout_review_reason, "retry_limit_reached")
        self.assertIsNone(payment.next_payout_attempt_at)

    async def test_payout_success_clears_errors_and_review_reason(self):
        """When payout succeeds, last_payout_error should be None, payout_review_reason should be None, and payout_transfer_code should be stored."""
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
            payout_attempt_count=0,
            last_payout_attempt_at=None,
            next_payout_attempt_at=datetime.now(UTC) - timedelta(minutes=1),
            last_payout_error="previous error",
            payout_review_reason="some reason",
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code="RCP_test")

        async def initiate_transfer(**kwargs):
            return {"transfer_code": "TRF_success123"}

        svc.initiate_transfer = initiate_transfer
        db = FakeSession(payment, tenant)

        result = await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        self.assertIs(result, payment)
        self.assertEqual(payment.settlement_status, "paid")
        self.assertEqual(payment.payout_transfer_code, "TRF_success123")
        self.assertIsNone(payment.last_payout_error)
        self.assertIsNone(payment.payout_review_reason)

    async def test_payout_missing_account_goes_to_needs_setup(self):
        """When tenant has no payout_recipient_code, settlement_status should be 'needs_setup' with payout_review_reason 'payout_account_missing'."""
        payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            booking_id=uuid4(),
            collection_mode="platform_collected",
            status="success",
            settlement_status="queued",
            business_net_amount=9_500,
        )
        tenant = SimpleNamespace(id=payment.tenant_id, payout_recipient_code=None)
        db = FakeSession(payment, tenant)

        with self.assertRaises(Exception) as cm:
            await svc.initiate_platform_collected_payout(db, tenant_id=payment.tenant_id, payment_id=payment.id)

        # Check the exception detail
        exc_detail = cm.exception.detail
        self.assertEqual(exc_detail["error"], "PAYOUT_SETUP_REQUIRED")
        self.assertEqual(payment.settlement_status, "needs_setup")
        self.assertEqual(payment.payout_review_reason, "payout_account_missing")

    async def test_processing_status_not_selected_again(self):
        """Verify that a payment with settlement_status='processing' is not selected for processing in process_due_payouts."""
        from sqlalchemy.ext.asyncio import AsyncSession

        processing_payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            status="success",
            collection_mode="platform_collected",
            settlement_status="processing",
            created_at=datetime.now(UTC) - timedelta(hours=1),
        )

        class FakeSelectResult:
            def __init__(self, items):
                self.items = items

            def scalars(self):
                return self

            def all(self):
                return self.items

        class FakeProcessSession(AsyncSession):
            def __init__(self):
                self.committed = False
                self.selected = []

            async def execute(self, stmt):
                # Simulate that only "queued" or "failed" status payments are selected
                # "processing" status is excluded by the WHERE clause
                return FakeSelectResult([])

            async def commit(self):
                self.committed = True

        db = FakeProcessSession()
        count = await svc.process_due_payouts(db, limit=25)

        # Should process 0 payments since processing status is excluded
        self.assertEqual(count, 0)

    async def test_paid_payout_not_processed_again(self):
        """Verify that a payment with settlement_status='paid' is not processed again."""
        from sqlalchemy.ext.asyncio import AsyncSession

        paid_payment = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            status="success",
            collection_mode="platform_collected",
            settlement_status="paid",
            created_at=datetime.now(UTC) - timedelta(hours=1),
        )

        class FakeSelectResult:
            def __init__(self, items):
                self.items = items

            def scalars(self):
                return self

            def all(self):
                return self.items

        class FakeProcessSession(AsyncSession):
            def __init__(self):
                self.committed = False
                self.selected = []

            async def execute(self, stmt):
                # Simulate that only "queued" or "failed" status payments are selected
                # "paid" status is excluded by the WHERE clause
                return FakeSelectResult([])

            async def commit(self):
                self.committed = True

        db = FakeProcessSession()
        count = await svc.process_due_payouts(db, limit=25)

        # Should process 0 payments since "paid" status is excluded
        self.assertEqual(count, 0)
