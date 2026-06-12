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

from app.routers import public as public_router  # noqa: E402
from app.schemas.assistant import AssistantRequest  # noqa: E402
from app.schemas.assistant import AssistantResponse  # noqa: E402
from app.services.booking_management_service import hash_manage_token  # noqa: E402


class FakeResult:
    def __init__(self, scalar=None, rows=None):
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def one_or_none(self):
        if not self.rows:
            return None
        return self.rows[0]


class FakeSession:
    def __init__(self, results):
        self.results = list(results)

    async def execute(self, _stmt):
        return self.results.pop(0)


class FakeTenantLookupSession:
    def __init__(self, tenant):
        self.tenant = tenant
        self.statements = []

    async def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        if params and "tenant_id" in params:
            return FakeResult()
        return FakeResult(scalar=self.tenant)


class PublicRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_get_public_tenant = public_router.get_public_tenant
        self.original_answer_public_assistant_message = getattr(public_router, "answer_public_assistant_message", None)

    def tearDown(self) -> None:
        public_router.get_public_tenant = self.original_get_public_tenant
        if self.original_answer_public_assistant_message is not None:
            public_router.answer_public_assistant_message = self.original_answer_public_assistant_message

    async def test_public_staff_rejects_service_outside_tenant(self):
        tenant = SimpleNamespace(id=uuid4())

        async def get_public_tenant(_db, _slug):
            return tenant

        public_router.get_public_tenant = get_public_tenant

        with self.assertRaises(Exception) as raised:
            await public_router.public_staff.__wrapped__(
                SimpleNamespace(),
                "tenant-slug",
                FakeSession([FakeResult(scalar=None)]),
                service_id=uuid4(),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 404)
        self.assertEqual(raised.exception.detail["error"], "SERVICE_NOT_FOUND")

    async def test_public_staff_filters_to_staff_assigned_to_requested_service(self):
        tenant = SimpleNamespace(id=uuid4())
        service_id = uuid4()
        assigned_staff = [SimpleNamespace(id=uuid4(), name="Kemi Rhodes"), SimpleNamespace(id=uuid4(), name="Nora James")]

        async def get_public_tenant(_db, _slug):
            return tenant

        public_router.get_public_tenant = get_public_tenant

        response = await public_router.public_staff.__wrapped__(
            SimpleNamespace(),
            "tenant-slug",
            FakeSession([FakeResult(scalar=service_id), FakeResult(rows=assigned_staff)]),
            service_id=service_id,
        )

        self.assertEqual([staff.name for staff in response], ["Kemi Rhodes", "Nora James"])

    async def test_get_public_tenant_sets_tenant_context_after_slug_lookup(self):
        tenant = SimpleNamespace(id=uuid4(), slug="tenant-slug", status="active")
        db = FakeTenantLookupSession(tenant)

        resolved = await self.original_get_public_tenant(db, "tenant-slug")

        self.assertEqual(resolved, tenant)
        self.assertEqual(db.statements[1][1], {"tenant_id": str(tenant.id)})
        self.assertIn("set_config('app.current_tenant_id'", db.statements[1][0])

    async def test_public_inspo_asset_returns_database_image_bytes(self):
        tenant = SimpleNamespace(id=uuid4())
        asset = SimpleNamespace(data=b"image-bytes", content_type="image/jpeg")

        async def get_public_tenant(_db, _slug):
            return tenant

        public_router.get_public_tenant = get_public_tenant

        response = await public_router.public_inspo_asset.__wrapped__(
            SimpleNamespace(),
            "tenant-slug",
            "stored-id",
            FakeSession([FakeResult(scalar=asset)]),
        )

        self.assertEqual(response.body, b"image-bytes")
        self.assertEqual(response.media_type, "image/jpeg")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    async def test_public_booking_status_without_token_returns_minimal_state(self):
        tenant = SimpleNamespace(id=uuid4())
        booking = SimpleNamespace(
            id=uuid4(),
            status="confirmed",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
            deposit_amount=5_000,
            price_status="fixed",
            quoted_price=None,
            manage_token_hash=hash_manage_token("valid-token"),
        )
        payment = SimpleNamespace(status="success", paystack_reference="bk_secret")
        service = SimpleNamespace(name="Private Service")
        staff = SimpleNamespace(name="Private Staff")

        async def get_public_tenant(_db, _slug):
            return tenant

        public_router.get_public_tenant = get_public_tenant

        response = await public_router.public_booking_status.__wrapped__(
            SimpleNamespace(),
            "tenant-slug",
            booking.id,
            FakeSession([FakeResult(rows=[(booking, payment, service, staff)])]),
        )

        self.assertEqual(response.booking_status, "confirmed")
        self.assertEqual(response.payment_status, "success")
        self.assertIsNone(response.reference)
        self.assertIsNone(response.start_time)
        self.assertIsNone(response.service_name)
        self.assertIsNone(response.manage_url)

    async def test_public_booking_status_with_invalid_token_returns_minimal_state(self):
        tenant = SimpleNamespace(id=uuid4())
        booking = SimpleNamespace(
            id=uuid4(),
            status="pending_payment",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
            deposit_amount=5_000,
            price_status="fixed",
            quoted_price=None,
            manage_token_hash=hash_manage_token("valid-token"),
        )
        payment = SimpleNamespace(status="pending", paystack_reference="bk_secret")

        async def get_public_tenant(_db, _slug):
            return tenant

        public_router.get_public_tenant = get_public_tenant

        response = await public_router.public_booking_status.__wrapped__(
            SimpleNamespace(),
            "tenant-slug",
            booking.id,
            FakeSession([FakeResult(rows=[(booking, payment, SimpleNamespace(name="Service"), SimpleNamespace(name="Staff"))])]),
            token="wrong-token",
        )

        self.assertEqual(response.booking_status, "pending_payment")
        self.assertIsNone(response.reference)
        self.assertIsNone(response.deposit_amount)
        self.assertIsNone(response.manage_url)

    async def test_public_booking_status_with_valid_token_returns_full_details(self):
        tenant = SimpleNamespace(id=uuid4())
        booking = SimpleNamespace(
            id=uuid4(),
            status="confirmed",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(hours=1),
            deposit_amount=5_000,
            price_status="fixed",
            quoted_price=None,
            manage_token_hash=hash_manage_token("valid-token"),
        )
        payment = SimpleNamespace(status="success", paystack_reference="bk_secret")
        service = SimpleNamespace(name="Braids")
        staff = SimpleNamespace(name="Ada")

        async def get_public_tenant(_db, _slug):
            return tenant

        public_router.get_public_tenant = get_public_tenant

        response = await public_router.public_booking_status.__wrapped__(
            SimpleNamespace(),
            "tenant-slug",
            booking.id,
            FakeSession([FakeResult(rows=[(booking, payment, service, staff)])]),
            token="valid-token",
        )

        self.assertEqual(response.reference, "bk_secret")
        self.assertEqual(response.service_name, "Braids")
        self.assertEqual(response.staff_name, "Ada")
        self.assertEqual(response.deposit_amount, 5_000)
        self.assertIn("token=valid-token", response.manage_url)

    async def test_public_assistant_resolves_tenant_by_slug_and_delegates(self):
        tenant = SimpleNamespace(id=uuid4(), name="LeTest Beauty Salon")
        seen = {}

        async def get_public_tenant(db, slug):
            seen["db"] = db
            seen["slug"] = slug
            return tenant

        async def answer_public_assistant_message(db, *, tenant, slug, payload):
            seen["assistant"] = (db, tenant, slug, payload)
            return AssistantResponse(reply="Hello", intent="fallback", suggested_actions=[])

        public_router.get_public_tenant = get_public_tenant
        public_router.answer_public_assistant_message = answer_public_assistant_message

        db = FakeSession([])
        payload = AssistantRequest(message="What services do you offer?")
        response = await public_router.public_assistant.__wrapped__(SimpleNamespace(), "tenant-slug", payload, db)

        self.assertEqual(response.reply, "Hello")
        self.assertEqual(seen["slug"], "tenant-slug")
        self.assertIs(seen["assistant"][0], db)
        self.assertIs(seen["assistant"][1], tenant)
        self.assertEqual(seen["assistant"][2], "tenant-slug")
        self.assertEqual(seen["assistant"][3].message, "What services do you offer?")

    async def test_public_assistant_preserves_missing_tenant_404(self):
        async def get_public_tenant(_db, _slug):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail={"error": "TENANT_NOT_FOUND"})

        public_router.get_public_tenant = get_public_tenant

        with self.assertRaises(Exception) as raised:
            await public_router.public_assistant.__wrapped__(
                SimpleNamespace(),
                "missing-slug",
                AssistantRequest(message="Hello"),
                FakeSession([]),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 404)

    async def test_public_assistant_body_cannot_override_tenant_id(self):
        tenant = SimpleNamespace(id=uuid4(), name="Real Tenant")
        captured = {}

        async def get_public_tenant(_db, _slug):
            return tenant

        async def answer_public_assistant_message(_db, *, tenant, slug, payload):
            captured["tenant"] = tenant
            captured["payload"] = payload
            return AssistantResponse(reply="Safe", intent="fallback", suggested_actions=[])

        public_router.get_public_tenant = get_public_tenant
        public_router.answer_public_assistant_message = answer_public_assistant_message

        payload = AssistantRequest.model_validate({"message": "Hello", "tenant_id": str(uuid4())})
        response = await public_router.public_assistant.__wrapped__(SimpleNamespace(), "tenant-slug", payload, FakeSession([]))

        self.assertEqual(response.reply, "Safe")
        self.assertIs(captured["tenant"], tenant)
        self.assertFalse(hasattr(captured["payload"], "tenant_id"))
