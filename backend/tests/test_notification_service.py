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


class FakeOneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class CapturingSession:
    def __init__(self, value=None):
        self.value = value
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return FakeOneResult(self.value)


class LoggingSession(CapturingSession):
    def __init__(self):
        super().__init__()
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.executions = 0

    async def execute(self, _stmt):
        self.executions += 1
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

    async def post(self, url, *, json=None, data=None, headers=None, auth=None):
        self.calls.append({"url": url, "json": json, "data": data, "headers": headers, "auth": auth, "timeout": self.timeout})
        return FakeResponse()


class NotificationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_send_booking_reminder = svc.send_booking_reminder
        self.original_client = svc.httpx.AsyncClient
        self.original_resend_api_key = svc.settings.resend_api_key
        self.original_from_email = svc.settings.from_email
        self.original_twilio_account_sid = svc.settings.twilio_account_sid
        self.original_twilio_auth_token = svc.settings.twilio_auth_token
        self.original_twilio_whatsapp_from_number = svc.settings.twilio_whatsapp_from_number
        FakeAsyncClient.calls = []

    def tearDown(self) -> None:
        svc.send_booking_reminder = self.original_send_booking_reminder
        svc.httpx.AsyncClient = self.original_client
        svc.settings.resend_api_key = self.original_resend_api_key
        svc.settings.from_email = self.original_from_email
        svc.settings.twilio_account_sid = self.original_twilio_account_sid
        svc.settings.twilio_auth_token = self.original_twilio_auth_token
        svc.settings.twilio_whatsapp_from_number = self.original_twilio_whatsapp_from_number

    async def test_process_due_reminders_counts_only_sent_reminders(self):
        booking_a = SimpleNamespace(id=uuid4())
        booking_b = SimpleNamespace(id=uuid4())
        sent_by_booking = {booking_a.id: True, booking_b.id: False}

        async def send_booking_reminder(_db, booking, _reminder_type):
            return sent_by_booking[booking.id]

        svc.send_booking_reminder = send_booking_reminder

        sent_count = await svc.process_due_reminders(FakeSession([booking_a, booking_b]))

        self.assertEqual(sent_count, 2)

    async def test_process_due_reminders_uses_non_overlapping_catch_up_windows(self):
        db = FakeSession([])
        now = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)

        await svc.process_due_reminders(db, now=now)

        self.assertEqual(db.executions, 2)

    async def test_booking_reminder_uses_human_local_time(self):
        booking = SimpleNamespace(
            id=uuid4(),
            tenant_id=uuid4(),
            start_time=datetime(2026, 8, 6, 10, 45, tzinfo=UTC),
        )
        tenant = SimpleNamespace(id=booking.tenant_id, name="Bookie Launch Studio", timezone="Africa/Lagos")
        client = SimpleNamespace(full_name="Opeyemi", email="client@example.com", whatsapp_number=None)
        service = SimpleNamespace(name="Consultation")
        staff = SimpleNamespace(name="Ayo")
        captured = {}
        original_context = svc.load_booking_context
        original_email = svc.send_and_log_email

        async def load_context(_db, _booking):
            return tenant, client, service, staff

        async def send_email(_db, **kwargs):
            captured.update(kwargs)
            return True

        svc.load_booking_context = load_context
        svc.send_and_log_email = send_email
        try:
            sent = await svc.send_booking_reminder(SimpleNamespace(), booking, "booking_reminder_24h")
        finally:
            svc.load_booking_context = original_context
            svc.send_and_log_email = original_email

        self.assertTrue(sent)
        self.assertIn("Thursday, 6 August 2026 at 11:45 AM", captured["text"])
        self.assertNotIn("2026-08-06T", captured["text"])

    async def test_notification_dedupe_is_scoped_to_recipient(self):
        db = CapturingSession()

        was_sent = await svc.notification_already_sent(
            db,
            uuid4(),
            "owner",
            "email",
            "booking_confirmation",
        )

        self.assertFalse(was_sent)
        sql = str(db.statement)
        self.assertIn("notification_log.recipient_type", sql)
        self.assertIn("notification_log.channel", sql)
        self.assertIn("notification_log.type", sql)

    async def test_send_email_posts_resend_payload(self):
        svc.httpx.AsyncClient = FakeAsyncClient
        svc.settings.resend_api_key = "re_test"
        svc.settings.from_email = "bookings@example.com"

        sent = await svc.send_email(
            to_email="client@example.com",
            subject="Booking confirmed",
            text="Your appointment is confirmed.",
            html="<p>Your appointment is confirmed.</p>",
        )

        self.assertTrue(sent)
        self.assertEqual(len(FakeAsyncClient.calls), 1)
        call = FakeAsyncClient.calls[0]
        self.assertEqual(call["url"], "https://api.resend.com/emails")
        self.assertEqual(call["headers"]["Authorization"], "Bearer re_test")
        self.assertEqual(call["json"]["from"], "bookings@example.com")
        self.assertEqual(call["json"]["to"], ["client@example.com"])
        self.assertEqual(call["json"]["subject"], "Booking confirmed")
        self.assertEqual(call["json"]["text"], "Your appointment is confirmed.")
        self.assertEqual(call["json"]["html"], "<p>Your appointment is confirmed.</p>")

    def test_booking_confirmation_content_is_human_and_actionable(self):
        booking_id = uuid4()
        manage_url = f"https://bookie.example/book/studio/manage/{booking_id}?token=secure-token"

        text, html = svc.build_booking_confirmation_content(
            client_name="Opeyemi Ogunbanwo",
            tenant_name="Bookie Launch Studio",
            service_name="Consultation",
            staff_name="Ayo",
            start_time=datetime(2026, 8, 6, 10, 45, tzinfo=UTC),
            timezone="Africa/Lagos",
            manage_url=manage_url,
        )

        self.assertIn("Thursday, 6 August 2026 at 11:45 AM", text)
        self.assertIn("Manage your booking", html)
        self.assertIn("Button not working?", html)
        self.assertIn(manage_url, html)
        self.assertNotIn("Reference", text)
        self.assertNotIn(str(booking_id), text.replace(manage_url, ""))

    def test_whatsapp_confirmation_omits_internal_reference(self):
        body = svc.format_whatsapp_body(
            "booking_confirmation",
            ["Ada", "Braids", "Mina", "Monday, 1 June 2026 at 10:00 AM", "internal-booking-id"],
        )

        self.assertIn("Monday, 1 June 2026 at 10:00 AM", body)
        self.assertNotIn("internal-booking-id", body)
        self.assertNotIn("Reference", body)

    async def test_logged_email_uses_recipient_scoped_provider_idempotency(self):
        svc.httpx.AsyncClient = FakeAsyncClient
        svc.settings.resend_api_key = "re_test"
        svc.settings.from_email = "bookings@example.com"
        booking = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
        db = LoggingSession()

        sent = await svc.send_and_log_email(
            db,
            booking=booking,
            recipient_type="owner",
            notification_type="booking_confirmation",
            to_email="owner@example.com",
            subject="New booking",
            text="A customer booked.",
        )

        self.assertTrue(sent)
        self.assertEqual(
            FakeAsyncClient.calls[0]["headers"]["Idempotency-Key"],
            f"notification:{booking.id}:owner:email:booking_confirmation",
        )

    async def test_send_whatsapp_template_posts_twilio_payload(self):
        svc.httpx.AsyncClient = FakeAsyncClient
        svc.settings.twilio_account_sid = "AC123"
        svc.settings.twilio_auth_token = "auth_test"
        svc.settings.twilio_whatsapp_from_number = "+2349000000000"

        sent = await svc.send_whatsapp_template(
            to_number="+2348000000000",
            template_name="booking_confirmation",
            body_params=["Ada", "Braids", "Mina", "2026-06-01T10:00:00Z", "booking-id"],
        )

        self.assertTrue(sent)
        self.assertEqual(len(FakeAsyncClient.calls), 1)
        call = FakeAsyncClient.calls[0]
        self.assertEqual(call["url"], "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json")
        self.assertEqual(call["data"]["From"], "whatsapp:+2349000000000")
        self.assertEqual(call["data"]["To"], "whatsapp:+2348000000000")
        self.assertIn("Ada", call["data"]["Body"])
        self.assertEqual(call["auth"], ("AC123", "auth_test"))

    async def test_unconfigured_email_is_logged_as_failed_not_sent(self):
        svc.settings.resend_api_key = None
        svc.settings.from_email = None
        booking = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
        db = LoggingSession()

        sent = await svc.send_and_log_email(
            db,
            booking=booking,
            recipient_type="owner",
            notification_type="booking_confirmation",
            to_email="owner@example.com",
            subject="New booking",
            text="A customer booked.",
        )

        self.assertFalse(sent)
        self.assertTrue(db.committed)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].status, "failed")
        self.assertEqual(db.added[0].recipient_type, "owner")
        self.assertEqual(db.added[0].error_message, "Email provider is not configured")
