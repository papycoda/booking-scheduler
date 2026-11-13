import os
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.routers import bookings as dashboard  # noqa: E402
from app.schemas.dashboard import DashboardBookingStatusUpdate  # noqa: E402


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeRowResult:
    def __init__(self, row):
        self.row = row

    def one(self):
        return self.row


class FakeDashboardSession:
    def __init__(self, booking, row):
        self.booking = booking
        self.row = row
        self.committed = False
        self.execute_count = 0

    async def execute(self, _stmt):
        self.execute_count += 1
        if self.execute_count == 1:
            return FakeScalarResult(self.booking)
        return FakeRowResult(self.row)

    async def commit(self):
        self.committed = True


class DashboardRouterTests(unittest.IsolatedAsyncioTestCase):
    def make_row(self):
        booking = SimpleNamespace(
            id=uuid4(),
            status="confirmed",
            start_time=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
            end_time=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        )
        client = SimpleNamespace(full_name="Chioma Okafor", email="chioma@example.com")
        service = SimpleNamespace(name="Haircut")
        staff = SimpleNamespace(name="Ada")
        payment = SimpleNamespace(amount=10_000, status="success")
        return booking, client, service, staff, payment

    def test_booking_row_to_response_maps_joined_booking_detail(self):
        booking, *_ = row = self.make_row()

        response = dashboard.booking_row_to_response(row)

        self.assertEqual(response.id, booking.id)
        self.assertEqual(response.status, "confirmed")
        self.assertEqual(response.client_name, "Chioma Okafor")
        self.assertEqual(response.service_name, "Haircut")
        self.assertEqual(response.amount, 10_000)
        self.assertEqual(response.payment_status, "success")

    async def test_update_dashboard_booking_cancellation_marks_business_cancelled(self):
        booking, client, service, staff, payment = self.make_row()
        row = (booking, client, service, staff, payment)
        db = FakeDashboardSession(booking, row)

        response = await dashboard.update_dashboard_booking(
            booking.id,
            DashboardBookingStatusUpdate(status="cancelled", cancellation_reason="Shop closed"),
            SimpleNamespace(tenant_id=uuid4()),
            db,
        )

        self.assertTrue(db.committed)
        self.assertEqual(booking.status, "cancelled")
        self.assertEqual(booking.cancelled_by, "business")
        self.assertEqual(booking.cancellation_reason, "Shop closed")
        self.assertIsNotNone(booking.cancelled_at)
        self.assertEqual(response.status, "cancelled")

    async def test_approve_dashboard_payout_sends_first_payout_after_review(self):
        tenant_id = uuid4()
        payment_id = uuid4()
        payment = SimpleNamespace(
            id=payment_id,
            settlement_status="needs_review",
            payout_review_reason="first_payout",
        )
        queued = SimpleNamespace(
            id=payment_id,
            settlement_status="queued",
            payout_transfer_reference=None,
            payout_transfer_code=None,
        )
        paid = SimpleNamespace(
            id=payment_id,
            settlement_status="paid",
            payout_transfer_reference="payout_ref",
            payout_transfer_code="TRF_test",
        )
        calls = []

        async def approve_payout(_db, *, tenant_id, payment_id):
            calls.append(("approve", tenant_id, payment_id))
            return queued

        async def initiate_platform_collected_payout(_db, *, tenant_id, payment_id):
            calls.append(("initiate", tenant_id, payment_id))
            return paid

        original_approve = dashboard.approve_payout
        original_initiate = dashboard.initiate_platform_collected_payout
        dashboard.approve_payout = approve_payout
        dashboard.initiate_platform_collected_payout = initiate_platform_collected_payout
        try:
            response = await dashboard.approve_dashboard_payout(
                payment_id,
                SimpleNamespace(tenant_id=tenant_id, role="tenant_owner"),
                FakeDashboardSession(payment, None),
            )
        finally:
            dashboard.approve_payout = original_approve
            dashboard.initiate_platform_collected_payout = original_initiate

        self.assertEqual(calls, [("approve", tenant_id, payment_id), ("initiate", tenant_id, payment_id)])
        self.assertEqual(response.settlement_status, "paid")
        self.assertEqual(response.payout_transfer_code, "TRF_test")

    async def test_approve_dashboard_payout_keeps_retry_limit_in_review(self):
        payment = SimpleNamespace(
            id=uuid4(),
            settlement_status="needs_review",
            payout_review_reason="retry_limit_reached",
        )

        with self.assertRaises(Exception) as raised:
            await dashboard.approve_dashboard_payout(
                payment.id,
                SimpleNamespace(tenant_id=uuid4(), role="tenant_owner"),
                FakeDashboardSession(payment, None),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 403)
        self.assertEqual(raised.exception.detail["error"], "PAYOUT_REVIEW_REQUIRED")
