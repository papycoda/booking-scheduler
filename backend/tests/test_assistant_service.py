import os
import unittest
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.schemas.assistant import AssistantContext, AssistantRequest  # noqa: E402
from app.services import assistant_service as svc  # noqa: E402
from app.services.availability_service import AvailableSlot  # noqa: E402


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def execute(self, statement):
        self.statements.append(str(statement))
        return FakeResult(self.rows)


def service(name, *, tenant_id, price=25_000_00, duration=180, deposit_policy="tenant_default", deposit_amount=None, is_active=True):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        description=None,
        duration_minutes=duration,
        price=price,
        currency="NGN",
        pricing_mode="from",
        deposit_policy=deposit_policy,
        deposit_amount=deposit_amount,
        is_active=is_active,
    )


class AssistantServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_id = uuid4()
        self.other_tenant_id = uuid4()
        self.tenant = SimpleNamespace(
            id=self.tenant_id,
            name="LeTest Beauty Salon",
            slug="letest-beauty-salon",
            address="12 Admiralty Way, Lekki",
            phone="+2348012345678",
            timezone="Africa/Lagos",
            default_deposit_amount=5_000_00,
            cancellation_notice_hours=24,
        )
        self.braids = service("Braids", tenant_id=self.tenant_id)
        self.wig = service("Wig installation", tenant_id=self.tenant_id, price=15_000_00, duration=90)
        self.other_service = service("Private Massage", tenant_id=self.other_tenant_id, price=99_000_00, duration=60)
        self.original_generate_available_slots = svc.generate_available_slots

    def tearDown(self) -> None:
        svc.generate_available_slots = self.original_generate_available_slots

    async def answer(self, message, *, services=None, context=None, tenant=None):
        return await svc.answer_public_assistant_message(
            FakeSession(services if services is not None else [self.braids, self.wig]),
            tenant=tenant or self.tenant,
            slug="letest-beauty-salon",
            payload=AssistantRequest(message=message, context=context),
        )

    async def test_lists_tenant_services(self):
        response = await self.answer("What services do you offer?")

        self.assertEqual(response.intent, "list_services")
        self.assertIn("Braids", response.reply)
        self.assertIn("Wig installation", response.reply)
        self.assertEqual([action.type for action in response.suggested_actions][-1], "book_now")

    async def test_answers_service_price_with_deposit_and_duration(self):
        response = await self.answer("How much is braids?")

        self.assertEqual(response.intent, "service_price")
        self.assertIn("Braids", response.reply)
        self.assertIn("NGN 25,000", response.reply)
        self.assertIn("NGN 5,000", response.reply)
        self.assertIn("3 hours", response.reply)

    async def test_asks_for_clarification_when_service_is_not_matched(self):
        response = await self.answer("How much is nails?")

        self.assertEqual(response.intent, "service_price")
        self.assertIn("Which service do you mean?", response.reply)
        self.assertIn("Braids", response.reply)
        self.assertIn("Wig installation", response.reply)

    async def test_answers_business_location(self):
        response = await self.answer("Where are you located?")

        self.assertEqual(response.intent, "business_location")
        self.assertEqual(response.reply, "LeTest Beauty Salon is located at 12 Admiralty Way, Lekki.")

    async def test_answers_deposit_policy_for_selected_service(self):
        response = await self.answer(
            "Do I need to pay deposit?",
            context=AssistantContext(service_id=self.braids.id),
        )

        self.assertEqual(response.intent, "deposit_policy")
        self.assertIn("Braids", response.reply)
        self.assertIn("NGN 5,000", response.reply)

    async def test_answers_cancellation_policy(self):
        response = await self.answer("Can I cancel after booking?")

        self.assertEqual(response.intent, "cancellation_policy")
        self.assertEqual(response.reply, "You can cancel, but please do it at least 24 hours before your appointment.")

    async def test_never_returns_services_from_another_tenant(self):
        response = await self.answer("What services do you offer?", services=[self.braids, self.other_service])

        self.assertIn("Braids", response.reply)
        self.assertNotIn("Private Massage", response.reply)
        self.assertNotIn(str(self.other_service.id), str(response.suggested_actions))

    async def test_availability_requires_service_first(self):
        response = await self.answer("Are you available tomorrow?")

        self.assertEqual(response.intent, "available_slots")
        self.assertEqual(response.reply, "Which service would you like to book? Availability depends on the service.")

    async def test_returns_slots_when_service_and_date_are_known(self):
        start = datetime(2026, 6, 15, 9, 0, tzinfo=UTC)

        async def generate_available_slots(_db, **kwargs):
            self.assertEqual(kwargs["tenant_id"], self.tenant_id)
            self.assertEqual(kwargs["service_id"], self.braids.id)
            self.assertEqual(kwargs["requested_date"], date(2026, 6, 15))
            return [
                AvailableSlot(start_time=start, end_time=start + timedelta(hours=3), available_staff=(uuid4(),)),
                AvailableSlot(start_time=start + timedelta(hours=4), end_time=start + timedelta(hours=7), available_staff=(uuid4(),)),
            ]

        svc.generate_available_slots = generate_available_slots

        response = await self.answer(
            "Are you available?",
            context=AssistantContext(service_id=self.braids.id, selected_date=date(2026, 6, 15)),
        )

        self.assertEqual(response.intent, "available_slots")
        self.assertIn("Braids", response.reply)
        self.assertIn("10:00 AM", response.reply)
        self.assertEqual([action.type for action in response.suggested_actions].count("show_slots"), 2)

    async def test_weekend_wording_does_not_infer_a_date(self):
        response = await self.answer(
            "Can I book this weekend?",
            context=AssistantContext(service_id=self.braids.id),
        )

        self.assertEqual(response.intent, "available_slots")
        self.assertIn("Please choose a date", response.reply)

    async def test_limits_slot_suggestions_to_five(self):
        start = datetime(2026, 6, 15, 9, 0, tzinfo=UTC)

        async def generate_available_slots(_db, **_kwargs):
            return [
                AvailableSlot(start_time=start + timedelta(hours=index), end_time=start + timedelta(hours=index + 1), available_staff=(uuid4(),))
                for index in range(8)
            ]

        svc.generate_available_slots = generate_available_slots

        response = await self.answer(
            "Available?",
            context=AssistantContext(service_id=self.braids.id, selected_date=date(2026, 6, 15)),
        )

        self.assertEqual([action.type for action in response.suggested_actions].count("show_slots"), 5)
