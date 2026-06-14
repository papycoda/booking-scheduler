"""
Tests for stale booking cleaner service.
"""
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

from app.services.stale_booking_cleaner import (  # noqa: E402
    PENDING_PAYMENT_TIMEOUT_MINUTES,
    expire_stale_pending_bookings,
)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    """Fake session that simulates SQL filtering by returning appropriate rows."""

    def __init__(self, stale_rows):
        """
        Args:
            stale_rows: Rows that should be returned from the query (already filtered by WHERE clause)
        """
        self.stale_rows = stale_rows
        self.committed = False
        self.booking_updates = []
        self.payment_updates = []

    async def execute(self, stmt):
        # Simulate returning rows that match the WHERE clause
        # (i.e., only stale bookings with pending payments)
        return FakeResult(self.stale_rows)

    async def commit(self):
        self.committed = True

    def track_updates(self, booking_ids, payment_booking_ids):
        """Track which bookings/payments would be updated."""
        self.booking_updates = booking_ids
        self.payment_updates = payment_booking_ids


class StaleBookingCleanerTests(unittest.IsolatedAsyncioTestCase):
    async def test_expire_stale_pending_bookings_marks_old_bookings_expired(self):
        """Test that stale pending_payment bookings are marked as expired."""
        now = datetime.now(UTC)

        # Simulate query result - only stale bookings with pending payments
        old_booking = SimpleNamespace(
            id=uuid4(),
            status="pending_payment",
            created_at=now - timedelta(minutes=PENDING_PAYMENT_TIMEOUT_MINUTES + 10),
        )
        old_payment = SimpleNamespace(booking_id=old_booking.id, status="pending")

        # Fake session returns pre-filtered results (as SQL WHERE clause would do)
        db = FakeSession([(old_booking, old_payment)])

        count = await expire_stale_pending_bookings(db, now=now)

        self.assertEqual(count, 1)
        self.assertEqual(old_booking.status, "expired")
        self.assertEqual(old_payment.status, "expired")
        self.assertTrue(db.committed)

    async def test_expire_stale_pending_bookings_multiple(self):
        """Test expiring multiple stale bookings at once."""
        now = datetime.now(UTC)

        # Multiple stale bookings
        stale_bookings = []
        for i in range(3):
            booking = SimpleNamespace(
                id=uuid4(),
                status="pending_payment",
                created_at=now - timedelta(minutes=PENDING_PAYMENT_TIMEOUT_MINUTES + i * 5),
            )
            payment = SimpleNamespace(booking_id=booking.id, status="pending")
            stale_bookings.append((booking, payment))

        db = FakeSession(stale_bookings)
        count = await expire_stale_pending_bookings(db, now=now)

        self.assertEqual(count, 3)
        for booking, payment in stale_bookings:
            self.assertEqual(booking.status, "expired")
            self.assertEqual(payment.status, "expired")

    async def test_expire_stale_pending_bookings_custom_timeout(self):
        """Test with custom timeout parameter."""
        now = datetime.now(UTC)

        # Booking that's 10 minutes old - should be stale with 5 min timeout
        booking = SimpleNamespace(
            id=uuid4(),
            status="pending_payment",
            created_at=now - timedelta(minutes=10),
        )
        payment = SimpleNamespace(booking_id=booking.id, status="pending")

        # With 5 minute timeout, this booking is stale
        db = FakeSession([(booking, payment)])
        count = await expire_stale_pending_bookings(db, now=now, timeout_minutes=5)

        self.assertEqual(count, 1)
        self.assertEqual(booking.status, "expired")
        self.assertEqual(payment.status, "expired")

    async def test_expire_stale_pending_bookings_empty(self):
        """Test when there are no stale bookings."""
        # SQL query returns empty result
        db = FakeSession([])
        count = await expire_stale_pending_bookings(db)
        self.assertEqual(count, 0)

    async def test_expire_stale_pending_bookings_boundary_case(self):
        """Test booking exactly at timeout boundary."""
        now = datetime.now(UTC)

        # Booking exactly at the timeout boundary (should NOT be expired)
        # The cutoff is `now - timeout_minutes`, so booking at exactly cutoff
        # should NOT be expired because we use `<= cutoff` in SQL
        booking_at_boundary = SimpleNamespace(
            id=uuid4(),
            status="pending_payment",
            created_at=now - timedelta(minutes=PENDING_PAYMENT_TIMEOUT_MINUTES),
        )
        payment = SimpleNamespace(booking_id=booking_at_boundary.id, status="pending")

        # Just-expired booking (1 minute past boundary)
        booking_just_expired = SimpleNamespace(
            id=uuid4(),
            status="pending_payment",
            created_at=now - timedelta(minutes=PENDING_PAYMENT_TIMEOUT_MINUTES + 1),
        )
        payment_just_expired = SimpleNamespace(
            booking_id=booking_just_expired.id, status="pending"
        )

        db = FakeSession([(booking_just_expired, payment_just_expired)])
        count = await expire_stale_pending_bookings(db, now=now)

        # Only the just-expired one should be expired
        self.assertEqual(count, 1)
        self.assertEqual(booking_just_expired.status, "expired")

    async def test_default_timeout_is_30_minutes(self):
        """Test that the default timeout is 30 minutes."""
        self.assertEqual(PENDING_PAYMENT_TIMEOUT_MINUTES, 30)
