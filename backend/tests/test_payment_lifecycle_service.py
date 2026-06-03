import os
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.services import payment_lifecycle_service as svc  # noqa: E402


class FakeScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def scalars(self):
        return FakeScalarRows(self._rows)


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.committed = False

    async def execute(self, _stmt):
        return FakeResult(self.rows)

    async def commit(self):
        self.committed = True


class PaymentLifecycleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_expire_unpaid_bookings_marks_old_pending_payment_and_booking_expired(self):
        now = datetime.now(UTC)
        booking = SimpleNamespace(id=uuid4(), status="pending_payment", created_at=now - timedelta(minutes=20))
        payment = SimpleNamespace(booking_id=booking.id, status="pending")
        db = FakeSession([(booking, payment)])

        count = await svc.expire_unpaid_bookings(db, now=now, hold_minutes=15)

        self.assertEqual(count, 1)
        self.assertEqual(booking.status, "expired")
        self.assertEqual(payment.status, "expired")
        self.assertTrue(db.committed)
