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


class FakeResponse:
    def raise_for_status(self):
        return None


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


class NotificationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_send_booking_reminder = svc.send_booking_reminder
        self.original_client = svc.httpx.AsyncClient
        self.original_resend_api_key = svc.settings.resend_api_key
        self.original_from_email = svc.settings.from_email
        self.original_meta_whatsapp_token = svc.settings.meta_whatsapp_token
        self.original_meta_whatsapp_phone_number_id = svc.settings.meta_whatsapp_phone_number_id
        FakeAsyncClient.calls = []

    def tearDown(self) -> None:
        svc.send_booking_reminder = self.original_send_booking_reminder
        svc.httpx.AsyncClient = self.original_client
        svc.settings.resend_api_key = self.original_resend_api_key
        svc.settings.from_email = self.original_from_email
        svc.settings.meta_whatsapp_token = self.original_meta_whatsapp_token
        svc.settings.meta_whatsapp_phone_number_id = self.original_meta_whatsapp_phone_number_id

    async def test_process_due_reminders_counts_only_sent_reminders(self):
        booking_a = SimpleNamespace(id=uuid4())
        booking_b = SimpleNamespace(id=uuid4())
        sent_by_booking = {booking_a.id: True, booking_b.id: False}

        async def send_booking_reminder(_db, booking, _reminder_type):
            return sent_by_booking[booking.id]

        svc.send_booking_reminder = send_booking_reminder

        sent_count = await svc.process_due_reminders(FakeSession([booking_a, booking_b]))

        self.assertEqual(sent_count, 2)

    async def test_send_email_posts_resend_payload(self):
        svc.httpx.AsyncClient = FakeAsyncClient
        svc.settings.resend_api_key = "re_test"
        svc.settings.from_email = "bookings@example.com"

        await svc.send_email(
            to_email="client@example.com",
            subject="Booking confirmed",
            text="Your appointment is confirmed.",
            html="<p>Your appointment is confirmed.</p>",
        )

        self.assertEqual(len(FakeAsyncClient.calls), 1)
        call = FakeAsyncClient.calls[0]
        self.assertEqual(call["url"], "https://api.resend.com/emails")
        self.assertEqual(call["headers"]["Authorization"], "Bearer re_test")
        self.assertEqual(call["json"]["from"], "bookings@example.com")
        self.assertEqual(call["json"]["to"], ["client@example.com"])
        self.assertEqual(call["json"]["subject"], "Booking confirmed")
        self.assertEqual(call["json"]["text"], "Your appointment is confirmed.")
        self.assertEqual(call["json"]["html"], "<p>Your appointment is confirmed.</p>")

    async def test_send_whatsapp_template_posts_meta_payload(self):
        svc.httpx.AsyncClient = FakeAsyncClient
        svc.settings.meta_whatsapp_token = "meta_test"
        svc.settings.meta_whatsapp_phone_number_id = "123456"

        await svc.send_whatsapp_template(
            to_number="+2348000000000",
            template_name="booking_confirmation",
            body_params=["Ada", "Braids", "Mina", "2026-06-01T10:00:00Z", "booking-id"],
        )

        self.assertEqual(len(FakeAsyncClient.calls), 1)
        call = FakeAsyncClient.calls[0]
        self.assertEqual(call["url"], "https://graph.facebook.com/v20.0/123456/messages")
        self.assertEqual(call["headers"]["Authorization"], "Bearer meta_test")
        self.assertEqual(call["json"]["messaging_product"], "whatsapp")
        self.assertEqual(call["json"]["to"], "+2348000000000")
        self.assertEqual(call["json"]["template"]["name"], "booking_confirmation")
        params = call["json"]["template"]["components"][0]["parameters"]
        self.assertEqual([param["text"] for param in params], ["Ada", "Braids", "Mina", "2026-06-01T10:00:00Z", "booking-id"])
