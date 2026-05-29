import os
import unittest
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.services import availability_service as svc  # noqa: E402


class AvailabilityServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_id = uuid4()
        self.service_id = uuid4()
        self.staff_a = uuid4()
        self.staff_b = uuid4()
        self.requested_date = date(2026, 6, 1)
        self.now = datetime(2026, 5, 30, 8, 0, tzinfo=UTC)
        self.tenant = SimpleNamespace(
            id=self.tenant_id,
            timezone="Africa/Lagos",
            booking_buffer_minutes=15,
            min_notice_hours=2,
            advance_booking_days=30,
        )
        self.service = SimpleNamespace(id=self.service_id, duration_minutes=60)
        self.staff = [SimpleNamespace(id=self.staff_a), SimpleNamespace(id=self.staff_b)]
        self.windows = {
            self.staff_a: [svc.LocalWindow(time(9, 0), time(12, 0))],
            self.staff_b: [svc.LocalWindow(time(9, 0), time(12, 0))],
        }
        self.bookings = {self.staff_a: [], self.staff_b: []}
        self._patch_loaders()

    def _patch_loaders(self) -> None:
        self.originals = {
            "load_tenant": svc.load_tenant,
            "load_service": svc.load_service,
            "load_candidate_staff": svc.load_candidate_staff,
            "load_working_windows": svc.load_working_windows,
            "load_bookings_for_local_date": svc.load_bookings_for_local_date,
        }

        async def load_tenant(_db, tenant_id):
            return self.tenant

        async def load_service(_db, tenant_id, service_id):
            return self.service

        async def load_candidate_staff(_db, *, tenant_id, service_id, staff_id):
            if staff_id is not None:
                return [staff for staff in self.staff if staff.id == staff_id]
            return self.staff

        async def load_working_windows(_db, tenant_id, staff_id, requested_date):
            return self.windows.get(staff_id, [])

        async def load_bookings_for_local_date(_db, tenant_id, staff_id, requested_date, tenant_zone):
            return self.bookings.get(staff_id, [])

        svc.load_tenant = load_tenant
        svc.load_service = load_service
        svc.load_candidate_staff = load_candidate_staff
        svc.load_working_windows = load_working_windows
        svc.load_bookings_for_local_date = load_bookings_for_local_date

    def tearDown(self) -> None:
        for name, original in self.originals.items():
            setattr(svc, name, original)

    async def generate(self, staff_id=None, requested_date=None, now=None):
        return await svc.generate_available_slots(
            None,
            tenant_id=self.tenant_id,
            service_id=self.service_id,
            requested_date=requested_date or self.requested_date,
            staff_id=staff_id,
            now=now or self.now,
        )

    async def test_basic_weekday_slot_generation(self):
        slots = await self.generate(staff_id=self.staff_a)

        self.assertEqual([slot.start_time.hour for slot in slots], [8, 9])
        self.assertTrue(all(slot.available_staff == (self.staff_a,) for slot in slots))

    async def test_existing_booking_blocks_overlapping_slot(self):
        self.bookings[self.staff_a] = [
            SimpleNamespace(
                start_time=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
                end_time=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            )
        ]

        slots = await self.generate(staff_id=self.staff_a)

        self.assertEqual([slot.start_time.hour for slot in slots], [8])

    async def test_full_day_override_blocks_all_slots(self):
        self.windows[self.staff_a] = []

        slots = await self.generate(staff_id=self.staff_a)

        self.assertEqual(slots, [])

    async def test_custom_hours_override_replaces_weekly_schedule(self):
        self.windows[self.staff_a] = [svc.LocalWindow(time(13, 0), time(15, 0))]

        slots = await self.generate(staff_id=self.staff_a)

        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0].start_time.hour, 12)

    async def test_anyone_mode_merges_slots_across_staff(self):
        self.bookings[self.staff_a] = [
            SimpleNamespace(
                start_time=datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
                end_time=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
            )
        ]

        slots = await self.generate()

        self.assertEqual(len(slots), 2)
        self.assertEqual(set(slots[0].available_staff), {self.staff_b})
        self.assertEqual(set(slots[1].available_staff), {self.staff_a, self.staff_b})

    async def test_slots_within_min_notice_are_excluded(self):
        close_now = datetime(2026, 6, 1, 6, 30, tzinfo=UTC)

        slots = await self.generate(staff_id=self.staff_a, now=close_now)

        self.assertEqual([slot.start_time.hour for slot in slots], [9])

    async def test_slots_beyond_advance_booking_days_are_rejected(self):
        with self.assertRaises(Exception) as raised:
            await self.generate(staff_id=self.staff_a, requested_date=date(2026, 7, 30))

        self.assertEqual(getattr(raised.exception, "status_code", None), 400)
