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

from app.services import notification_service as svc  # noqa: E402


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return FakeScalarResult(self.rows)


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _stmt):
        return FakeResult(self.rows)


class NotificationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_send_booking_reminder = svc.send_booking_reminder

    def tearDown(self) -> None:
        svc.send_booking_reminder = self.original_send_booking_reminder

    async def test_process_due_reminders_counts_only_sent_reminders(self):
        booking_a = SimpleNamespace(id=uuid4())
        booking_b = SimpleNamespace(id=uuid4())
        sent_by_booking = {booking_a.id: True, booking_b.id: False}

        async def send_booking_reminder(_db, booking, _reminder_type):
            return sent_by_booking[booking.id]

        svc.send_booking_reminder = send_booking_reminder

        sent_count = await svc.process_due_reminders(FakeSession([booking_a, booking_b]))

        self.assertEqual(sent_count, 2)
