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

from app.routers.staff import assign_staff_services, delete_staff, read_staff  # noqa: E402
from app.schemas.staff import StaffServiceAssignmentRequest  # noqa: E402


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
        self.executed = []
        self.commits = 0

    async def execute(self, stmt, params=None):
        self.executed.append((stmt, params))
        return self.results.pop(0)

    async def commit(self):
        self.commits += 1


class StaffRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_staff_returns_404_when_not_in_current_tenant(self):
        with self.assertRaises(Exception) as raised:
            await read_staff(uuid4(), SimpleNamespace(tenant_id=uuid4()), FakeSession([FakeResult(scalar=None)]))

        self.assertEqual(getattr(raised.exception, "status_code", None), 404)

    async def test_delete_staff_soft_deletes_current_tenant_staff(self):
        staff = SimpleNamespace(is_active=True)
        db = FakeSession([FakeResult(scalar=staff)])

        await delete_staff(uuid4(), SimpleNamespace(tenant_id=uuid4()), db)

        self.assertFalse(staff.is_active)
        self.assertEqual(db.commits, 1)

    async def test_assign_staff_services_rejects_cross_tenant_service_ids(self):
        requested_service_id = uuid4()
        db = FakeSession(
            [
                FakeResult(scalar=SimpleNamespace(id=uuid4())),
                FakeResult(scalars=[]),
            ]
        )

        with self.assertRaises(Exception) as raised:
            await assign_staff_services(
                uuid4(),
                StaffServiceAssignmentRequest(service_ids=[requested_service_id]),
                SimpleNamespace(tenant_id=uuid4()),
                db,
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 400)
        self.assertEqual(db.commits, 0)
        self.assertEqual(len(db.executed), 2)

    async def test_assign_staff_services_replaces_service_links_when_all_services_are_tenant_owned(self):
        staff_id = uuid4()
        service_ids = [uuid4(), uuid4()]
        db = FakeSession(
            [
                FakeResult(scalar=SimpleNamespace(id=staff_id)),
                FakeResult(scalars=service_ids),
                FakeResult(),
                FakeResult(),
            ]
        )

        await assign_staff_services(
            staff_id,
            StaffServiceAssignmentRequest(service_ids=service_ids),
            SimpleNamespace(tenant_id=uuid4()),
            db,
        )

        inserted_rows = db.executed[-1][1]
        self.assertEqual(db.commits, 1)
        self.assertEqual(inserted_rows, [{"staff_id": staff_id, "service_id": service_id} for service_id in service_ids])
