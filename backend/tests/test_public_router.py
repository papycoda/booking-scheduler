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

from app.routers import public as public_router  # noqa: E402


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

    def tearDown(self) -> None:
        public_router.get_public_tenant = self.original_get_public_tenant

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

    async def test_get_public_tenant_sets_tenant_context_after_slug_lookup(self):
        tenant = SimpleNamespace(id=uuid4(), slug="tenant-slug", status="active")
        db = FakeTenantLookupSession(tenant)

        resolved = await self.original_get_public_tenant(db, "tenant-slug")

        self.assertEqual(resolved, tenant)
        self.assertEqual(db.statements[1][1], {"tenant_id": str(tenant.id)})
        self.assertIn("set_config('app.current_tenant_id'", db.statements[1][0])
