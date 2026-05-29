import os
import unittest
from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.routers.availability import create_override, create_schedule, delete_override, delete_schedule, update_schedule  # noqa: E402
from app.schemas.availability import AvailabilityOverrideCreateRequest, AvailabilityScheduleCreateRequest, AvailabilityScheduleUpdateRequest  # noqa: E402


class FakeResult:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class FakeSession:
    def __init__(self, row):
        self.row = row
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, _stmt):
        return FakeResult(self.row)

    def add(self, row):
        self.added.append(row)

    async def delete(self, row):
        self.deleted.append(row)

    async def commit(self):
        self.commits += 1

    async def refresh(self, row):
        self.refreshed.append(row)


class AvailabilityRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_schedule_update_rejects_invalid_final_time_range(self):
        schedule = SimpleNamespace(start_time=time(9, 0), end_time=time(10, 0), staff_id=None)
        payload = AvailabilityScheduleUpdateRequest(start_time=time(11, 0))

        with self.assertRaises(Exception) as raised:
            await update_schedule(
                uuid4(),
                payload,
                SimpleNamespace(tenant_id=uuid4()),
                FakeSession(schedule),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 422)

    async def test_create_schedule_rejects_staff_from_another_tenant(self):
        payload = AvailabilityScheduleCreateRequest(staff_id=uuid4(), day_of_week=1, start_time=time(9, 0), end_time=time(17, 0))

        with self.assertRaises(Exception) as raised:
            await create_schedule(payload, SimpleNamespace(tenant_id=uuid4()), FakeSession(None))

        self.assertEqual(getattr(raised.exception, "status_code", None), 400)

    async def test_create_schedule_persists_tenant_scoped_schedule_when_staff_is_valid(self):
        tenant_id = uuid4()
        staff_id = uuid4()
        db = FakeSession(staff_id)

        schedule = await create_schedule(
            AvailabilityScheduleCreateRequest(staff_id=staff_id, day_of_week=2, start_time=time(9, 0), end_time=time(17, 0)),
            SimpleNamespace(tenant_id=tenant_id),
            db,
        )

        self.assertEqual(schedule.tenant_id, tenant_id)
        self.assertEqual(schedule.staff_id, staff_id)
        self.assertEqual(db.added, [schedule])
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.refreshed, [schedule])

    async def test_delete_schedule_removes_current_tenant_schedule_when_found(self):
        schedule = SimpleNamespace(id=uuid4())
        db = FakeSession(schedule)

        await delete_schedule(uuid4(), SimpleNamespace(tenant_id=uuid4()), db)

        self.assertEqual(db.deleted, [schedule])
        self.assertEqual(db.commits, 1)

    async def test_delete_schedule_is_idempotent_when_schedule_not_found(self):
        db = FakeSession(None)

        await delete_schedule(uuid4(), SimpleNamespace(tenant_id=uuid4()), db)

        self.assertEqual(db.deleted, [])
        self.assertEqual(db.commits, 0)

    async def test_create_override_persists_tenant_scoped_override_when_staff_is_valid(self):
        tenant_id = uuid4()
        staff_id = uuid4()
        db = FakeSession(staff_id)

        override = await create_override(
            AvailabilityOverrideCreateRequest(
                staff_id=staff_id,
                date=date(2026, 6, 1),
                start_time=time(10, 0),
                end_time=time(13, 0),
            ),
            SimpleNamespace(tenant_id=tenant_id),
            db,
        )

        self.assertEqual(override.tenant_id, tenant_id)
        self.assertEqual(override.staff_id, staff_id)
        self.assertEqual(db.added, [override])
        self.assertEqual(db.commits, 1)

    async def test_delete_override_removes_current_tenant_override_when_found(self):
        override = SimpleNamespace(id=uuid4())
        db = FakeSession(override)

        await delete_override(uuid4(), SimpleNamespace(tenant_id=uuid4()), db)

        self.assertEqual(db.deleted, [override])
        self.assertEqual(db.commits, 1)
