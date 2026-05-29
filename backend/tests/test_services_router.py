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

from app.routers.services import delete_service, list_services, update_service  # noqa: E402
from app.schemas.service import ServiceUpdateRequest  # noqa: E402


class FakeResult:
    def __init__(self, scalar=None, scalars=None):
        self.scalar = scalar
        self._scalars = scalars or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return self

    def all(self):
        return self._scalars


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.commits = 0
        self.refreshed = []

    async def execute(self, _stmt):
        return self.results.pop(0)

    async def commit(self):
        self.commits += 1

    async def refresh(self, row):
        self.refreshed.append(row)


class ServicesRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_services_returns_query_result_for_current_tenant_active_services(self):
        services = [SimpleNamespace(name="Braids"), SimpleNamespace(name="Locs")]

        result = await list_services(SimpleNamespace(tenant_id=uuid4()), FakeSession([FakeResult(scalars=services)]))

        self.assertEqual(result, services)

    async def test_update_service_mutates_only_supplied_fields(self):
        service = SimpleNamespace(name="Braids", duration_minutes=30, price=1000, is_active=True)
        db = FakeSession([FakeResult(scalar=service)])

        result = await update_service(
            uuid4(),
            ServiceUpdateRequest(price=1500),
            SimpleNamespace(tenant_id=uuid4()),
            db,
        )

        self.assertIs(result, service)
        self.assertEqual(service.name, "Braids")
        self.assertEqual(service.price, 1500)
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.refreshed, [service])

    async def test_delete_service_soft_deletes_current_tenant_service(self):
        service = SimpleNamespace(is_active=True)
        db = FakeSession([FakeResult(scalar=service)])

        await delete_service(uuid4(), SimpleNamespace(tenant_id=uuid4()), db)

        self.assertFalse(service.is_active)
        self.assertEqual(db.commits, 1)

    async def test_delete_service_raises_404_for_cross_tenant_service(self):
        with self.assertRaises(Exception) as raised:
            await delete_service(uuid4(), SimpleNamespace(tenant_id=uuid4()), FakeSession([FakeResult(scalar=None)]))

        self.assertEqual(getattr(raised.exception, "status_code", None), 404)
