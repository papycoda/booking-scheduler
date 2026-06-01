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

from app.schemas.booking import PublicRescheduleRequestCreate  # noqa: E402
from app.services import booking_management_service as svc  # noqa: E402
from app.services.availability_service import AvailableSlot  # noqa: E402


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class FakeRowResult:
    def __init__(self, row):
        self.row = row

    def one_or_none(self):
        return self.row

    def one(self):
        return self.row


class FakeRowsResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def scalars(self):
        return self


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []
        self.committed = False

    async def execute(self, _stmt):
        return self.results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()

    async def commit(self):
        self.committed = True


class BookingManagementServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_generate_available_slots = svc.generate_available_slots

    def tearDown(self) -> None:
        svc.generate_available_slots = self.original_generate_available_slots

    def test_manage_token_round_trips_without_storing_raw_token(self):
        raw_token, token_hash = svc.create_manage_token_pair()

        self.assertNotEqual(raw_token, token_hash)
        self.assertTrue(svc.verify_manage_token(raw_token, token_hash))
        self.assertFalse(svc.verify_manage_token("wrong-token", token_hash))

    async def test_client_cancellation_requires_valid_token_and_keeps_deposit(self):
        tenant = SimpleNamespace(id=uuid4(), cancellation_notice_hours=24)
        booking = SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant.id,
            status="confirmed",
            start_time=datetime.now(UTC) + timedelta(days=3),
            end_time=datetime.now(UTC) + timedelta(days=3, hours=1),
            manage_token_hash=svc.hash_manage_token("valid-token"),
            deposit_amount=5_000,
            cancellation_reason=None,
            cancelled_by=None,
            cancelled_at=None,
        )
        db = FakeSession([FakeScalarResult(booking), FakeRowsResult([])])

        await svc.cancel_client_booking(db, tenant=tenant, booking_id=booking.id, token="valid-token", reason="Plans changed")

        self.assertTrue(db.committed)
        self.assertEqual(booking.status, "cancelled")
        self.assertEqual(booking.cancelled_by, "client")
        self.assertEqual(booking.cancellation_reason, "Plans changed")
        self.assertEqual(booking.deposit_amount, 5_000)

    async def test_reschedule_request_creates_24_hour_hold_without_moving_booking(self):
        tenant_id = uuid4()
        booking_id = uuid4()
        staff_id = uuid4()
        service_id = uuid4()
        start_time = datetime.now(UTC) + timedelta(days=4)
        new_start = start_time + timedelta(days=1)
        new_end = new_start + timedelta(hours=1)
        tenant = SimpleNamespace(id=tenant_id, timezone="Africa/Lagos")
        booking = SimpleNamespace(
            id=booking_id,
            tenant_id=tenant_id,
            staff_id=staff_id,
            service_id=service_id,
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            status="confirmed",
            manage_token_hash=svc.hash_manage_token("valid-token"),
        )

        async def generate_available_slots(_db, **_kwargs):
            return [AvailableSlot(start_time=new_start, end_time=new_end, available_staff=(staff_id,))]

        svc.generate_available_slots = generate_available_slots
        db = FakeSession([FakeScalarResult(booking), FakeScalarResult(None)])

        response = await svc.create_reschedule_request(
            db,
            tenant=tenant,
            booking_id=booking_id,
            token="valid-token",
            payload=PublicRescheduleRequestCreate(start_time=new_start, staff_id=staff_id, note="Need later"),
        )

        request = db.added[0]
        self.assertTrue(db.committed)
        self.assertEqual(request.status, "pending")
        self.assertEqual(request.requested_start_time, new_start)
        self.assertEqual(request.requested_end_time, new_end)
        self.assertEqual(request.requested_staff_id, staff_id)
        self.assertEqual(request.client_note, "Need later")
        self.assertEqual(request.booking_id, booking_id)
        self.assertAlmostEqual((request.hold_expires_at - datetime.now(UTC)).total_seconds(), 24 * 60 * 60, delta=5)
        self.assertEqual(booking.start_time, start_time)
        self.assertEqual(response.status, "pending")

    async def test_approve_reschedule_request_updates_booking_only_after_owner_approval(self):
        tenant_id = uuid4()
        booking = SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant_id,
            start_time=datetime.now(UTC) + timedelta(days=3),
            end_time=datetime.now(UTC) + timedelta(days=3, hours=1),
            staff_id=uuid4(),
            service_id=uuid4(),
            status="confirmed",
        )
        requested_staff_id = uuid4()
        request = SimpleNamespace(
            id=uuid4(),
            tenant_id=tenant_id,
            booking_id=booking.id,
            requested_staff_id=requested_staff_id,
            requested_start_time=booking.start_time + timedelta(days=1),
            requested_end_time=booking.end_time + timedelta(days=1),
            status="pending",
            hold_expires_at=datetime.now(UTC) + timedelta(hours=2),
            decided_at=None,
            decided_by_user_id=None,
            decision_note=None,
        )

        async def generate_available_slots(_db, **_kwargs):
            return [AvailableSlot(start_time=request.requested_start_time, end_time=request.requested_end_time, available_staff=(requested_staff_id,))]

        svc.generate_available_slots = generate_available_slots
        db = FakeSession([FakeRowResult((request, booking)), FakeScalarResult(None), FakeScalarResult(None)])

        await svc.decide_reschedule_request(
            db,
            tenant_id=tenant_id,
            request_id=request.id,
            user_id=uuid4(),
            decision="approved",
            note="OK",
        )

        self.assertTrue(db.committed)
        self.assertEqual(request.status, "approved")
        self.assertEqual(booking.start_time, request.requested_start_time)
        self.assertEqual(booking.end_time, request.requested_end_time)
        self.assertEqual(booking.staff_id, requested_staff_id)
