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

from app.schemas.booking import PublicBookingCreateRequest  # noqa: E402
from app.services import booking_service as svc  # noqa: E402
from app.services.availability_service import AvailableSlot  # noqa: E402


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _stmt):
        return FakeResult(self.rows)


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeBookingSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False

    def begin_nested(self):
        return FakeTransaction()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()

    async def execute(self, _stmt):
        return FakeScalarResult(None)

    async def commit(self):
        self.committed = True


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class BookingServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.originals = {
            "load_service": svc.load_service,
            "generate_available_slots": svc.generate_available_slots,
            "choose_staff_with_fewest_bookings": svc.choose_staff_with_fewest_bookings,
            "lock_staff_for_booking": svc.lock_staff_for_booking,
            "upsert_client": svc.upsert_client,
            "initialize_checkout_payment": svc.initialize_checkout_payment,
            "save_inspo_images": svc.save_inspo_images,
        }

    def tearDown(self) -> None:
        for name, original in self.originals.items():
            if original is not None:
                setattr(svc, name, original)

    async def test_choose_staff_with_fewest_bookings_prefers_lowest_count(self):
        staff_a = uuid4()
        staff_b = uuid4()
        staff_c = uuid4()
        db = FakeSession([(staff_a, 4), (staff_b, 1)])

        selected = await svc.choose_staff_with_fewest_bookings(
            db,
            tenant_id=uuid4(),
            staff_ids=(staff_a, staff_b, staff_c),
            start_time=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        )

        self.assertEqual(selected, staff_c)

    async def test_choose_staff_with_fewest_bookings_returns_none_without_candidates(self):
        selected = await svc.choose_staff_with_fewest_bookings(
            FakeSession([]),
            tenant_id=uuid4(),
            staff_ids=(),
            start_time=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        )

        self.assertIsNone(selected)

    async def test_create_public_booking_creates_pending_booking_payment_and_provider_metadata(self):
        tenant_id = uuid4()
        service_id = uuid4()
        staff_id = uuid4()
        client_id = uuid4()
        start_time = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        end_time = start_time + timedelta(hours=1)
        tenant = SimpleNamespace(
            id=tenant_id,
            timezone="Africa/Lagos",
            paystack_subaccount_code="ACCT_test",
            platform_fee_percentage=5,
            default_deposit_amount=2_500,
        )
        service = SimpleNamespace(
            id=service_id,
            name="Haircut",
            price=10_000,
            currency="NGN",
            pricing_mode="from",
            deposit_policy="tenant_default",
            deposit_amount=None,
        )
        staff = SimpleNamespace(id=staff_id, name="Ada")
        paystack_call = {}

        async def load_service(_db, _tenant_id, _service_id):
            return service

        async def generate_available_slots(_db, **_kwargs):
            return [AvailableSlot(start_time=start_time, end_time=end_time, available_staff=(staff_id,))]

        async def choose_staff_with_fewest_bookings(_db, _tenant_id, staff_ids, _start_time):
            return staff_ids[0]

        async def lock_staff_for_booking(_db, _tenant_id, _staff_id, _service_id):
            return staff

        async def upsert_client(_db, _tenant_id, _payload):
            return client_id

        async def initialize_checkout_payment(**kwargs):
            paystack_call.update(kwargs)
            return (
                {"authorization_url": "https://checkout.paystack.com/test", "access_code": "access_test"},
                SimpleNamespace(provider="paystack", collection_mode="direct_split", platform_fee_amount=125, business_net_amount=2_375),
            )

        svc.load_service = load_service
        svc.generate_available_slots = generate_available_slots
        svc.choose_staff_with_fewest_bookings = choose_staff_with_fewest_bookings
        svc.lock_staff_for_booking = lock_staff_for_booking
        svc.upsert_client = upsert_client
        svc.initialize_checkout_payment = initialize_checkout_payment

        db = FakeBookingSession()
        response = await svc.create_public_booking(
            db,
            tenant=tenant,
            slug="ada-hair",
            payload=PublicBookingCreateRequest(
                service_id=service_id,
                staff_id=None,
                start_time=start_time,
                client={
                    "full_name": "Chioma Okafor",
                    "email": "chioma@example.com",
                    "phone": "+2348012345678",
                    "whatsapp_number": "+2348012345678",
                },
                notes="Back chair",
            ),
        )

        booking = db.added[0]
        payment = db.added[1]
        self.assertTrue(db.committed)
        self.assertEqual(booking.status, "pending_payment")
        self.assertEqual(booking.staff_id, staff_id)
        self.assertEqual(booking.client_id, client_id)
        self.assertEqual(payment.booking_id, booking.id)
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.amount, 2_500)
        self.assertEqual(payment.payment_type, "deposit")
        self.assertEqual(booking.deposit_amount, 2_500)
        self.assertEqual(booking.price_status, "pending_quote")
        self.assertEqual(response.deposit_amount, 2_500)
        self.assertEqual(response.payment_url, "https://checkout.paystack.com/test")
        self.assertEqual(paystack_call["amount"], 2_500)
        self.assertEqual(paystack_call["metadata"]["payment_type"], "deposit")
        self.assertEqual(paystack_call["metadata"]["deposit_amount"], "2500")
        self.assertEqual(paystack_call["metadata"]["booking_id"], str(booking.id))
        self.assertEqual(paystack_call["metadata"]["tenant_id"], str(tenant_id))
        self.assertEqual(payment.collection_mode, "direct_split")
        self.assertEqual(payment.platform_fee_amount, 125)
        self.assertEqual(payment.business_net_amount, 2_375)

    async def test_create_public_booking_rejects_quote_service_without_deposit(self):
        tenant_id = uuid4()
        service_id = uuid4()
        start_time = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        tenant = SimpleNamespace(
            id=tenant_id,
            timezone="Africa/Lagos",
            paystack_subaccount_code="ACCT_test",
            platform_fee_percentage=5,
            default_deposit_amount=0,
        )
        service = SimpleNamespace(
            id=service_id,
            name="Braids",
            price=10_000,
            currency="NGN",
            pricing_mode="consultation",
            deposit_policy="tenant_default",
            deposit_amount=None,
        )

        async def load_service(_db, _tenant_id, _service_id):
            return service

        svc.load_service = load_service

        with self.assertRaises(Exception) as raised:
            await svc.create_public_booking(
                FakeBookingSession(),
                tenant=tenant,
                slug="ada-hair",
                payload=PublicBookingCreateRequest(
                    service_id=service_id,
                    start_time=start_time,
                    client={"full_name": "Chioma Okafor", "email": "chioma@example.com"},
                ),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 409)
        self.assertEqual(raised.exception.detail["error"], "DEPOSIT_REQUIRED")

    async def test_create_public_booking_uses_platform_collection_without_subaccount(self):
        tenant_id = uuid4()
        service_id = uuid4()
        staff_id = uuid4()
        client_id = uuid4()
        start_time = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        end_time = start_time + timedelta(hours=1)
        tenant = SimpleNamespace(
            id=tenant_id,
            timezone="Africa/Lagos",
            paystack_subaccount_code=None,
            payment_setup_status="not_started",
            platform_fee_percentage=5,
            default_deposit_amount=10_000,
        )
        service = SimpleNamespace(
            id=service_id,
            name="Haircut",
            price=25_000,
            currency="NGN",
            pricing_mode="fixed",
            deposit_policy="tenant_default",
            deposit_amount=None,
        )
        staff = SimpleNamespace(id=staff_id, name="Ada")
        paystack_call = {}

        async def load_service(_db, _tenant_id, _service_id):
            return service

        async def generate_available_slots(_db, **_kwargs):
            return [AvailableSlot(start_time=start_time, end_time=end_time, available_staff=(staff_id,))]

        async def choose_staff_with_fewest_bookings(_db, _tenant_id, staff_ids, _start_time):
            return staff_ids[0]

        async def lock_staff_for_booking(_db, _tenant_id, _staff_id, _service_id):
            return staff

        async def upsert_client(_db, _tenant_id, _payload):
            return client_id

        async def initialize_checkout_payment(**kwargs):
            paystack_call.update(kwargs)
            return (
                {"authorization_url": "https://checkout.paystack.com/test", "access_code": "access_test"},
                SimpleNamespace(provider="paystack", collection_mode="platform_collected", platform_fee_amount=500, business_net_amount=9_500),
            )

        svc.load_service = load_service
        svc.generate_available_slots = generate_available_slots
        svc.choose_staff_with_fewest_bookings = choose_staff_with_fewest_bookings
        svc.lock_staff_for_booking = lock_staff_for_booking
        svc.upsert_client = upsert_client
        svc.initialize_checkout_payment = initialize_checkout_payment

        db = FakeBookingSession()
        response = await svc.create_public_booking(
            db,
            tenant=tenant,
            slug="ada-hair",
            payload=PublicBookingCreateRequest(
                service_id=service_id,
                start_time=start_time,
                client={"full_name": "Chioma Okafor", "email": "chioma@example.com"},
            ),
        )

        payment = db.added[1]
        self.assertEqual(response.payment_url, "https://checkout.paystack.com/test")
        self.assertEqual(paystack_call["tenant"], tenant)
        self.assertEqual(payment.collection_mode, "platform_collected")
        self.assertEqual(payment.platform_fee_amount, 500)
        self.assertEqual(payment.business_net_amount, 9_500)
        self.assertEqual(payment.settlement_status, "not_due")

    async def test_create_public_booking_caps_platform_fee_at_ten_percent(self):
        tenant_id = uuid4()
        service_id = uuid4()
        staff_id = uuid4()
        client_id = uuid4()
        start_time = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        tenant = SimpleNamespace(
            id=tenant_id,
            timezone="Africa/Lagos",
            paystack_subaccount_code=None,
            payment_setup_status="not_started",
            platform_fee_percentage=25,
            default_deposit_amount=20_000,
        )
        service = SimpleNamespace(
            id=service_id,
            name="Braids",
            price=20_000,
            currency="NGN",
            pricing_mode="fixed",
            deposit_policy="tenant_default",
            deposit_amount=None,
        )
        staff = SimpleNamespace(id=staff_id, name="Ada")

        async def load_service(_db, _tenant_id, _service_id):
            return service

        async def generate_available_slots(_db, **_kwargs):
            return [AvailableSlot(start_time=start_time, end_time=start_time + timedelta(hours=1), available_staff=(staff_id,))]

        async def choose_staff_with_fewest_bookings(_db, _tenant_id, staff_ids, _start_time):
            return staff_ids[0]

        async def lock_staff_for_booking(_db, _tenant_id, _staff_id, _service_id):
            return staff

        async def upsert_client(_db, _tenant_id, _payload):
            return client_id

        async def initialize_checkout_payment(**_kwargs):
            return (
                {"authorization_url": "https://checkout.paystack.com/test", "access_code": "access_test"},
                SimpleNamespace(provider="paystack", collection_mode="platform_collected", platform_fee_amount=2_000, business_net_amount=18_000),
            )

        svc.load_service = load_service
        svc.generate_available_slots = generate_available_slots
        svc.choose_staff_with_fewest_bookings = choose_staff_with_fewest_bookings
        svc.lock_staff_for_booking = lock_staff_for_booking
        svc.upsert_client = upsert_client
        svc.initialize_checkout_payment = initialize_checkout_payment

        db = FakeBookingSession()
        await svc.create_public_booking(
            db,
            tenant=tenant,
            slug="ada-hair",
            payload=PublicBookingCreateRequest(
                service_id=service_id,
                start_time=start_time,
                client={"full_name": "Chioma Okafor", "email": "chioma@example.com"},
            ),
        )

        payment = db.added[1]
        self.assertEqual(payment.platform_fee_amount, 2_000)
        self.assertEqual(payment.business_net_amount, 18_000)

    async def test_create_public_booking_stores_inspo_assets(self):
        tenant_id = uuid4()
        service_id = uuid4()
        staff_id = uuid4()
        client_id = uuid4()
        start_time = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        end_time = start_time + timedelta(hours=1)
        tenant = SimpleNamespace(
            id=tenant_id,
            timezone="Africa/Lagos",
            paystack_subaccount_code="ACCT_test",
            platform_fee_percentage=5,
            default_deposit_amount=3_000,
        )
        service = SimpleNamespace(
            id=service_id,
            name="Braids",
            price=20_000,
            currency="NGN",
            pricing_mode="from",
            deposit_policy="tenant_default",
            deposit_amount=None,
        )
        staff = SimpleNamespace(id=staff_id, name="Ada")
        asset = SimpleNamespace(booking_id=None, tenant_id=tenant_id, original_filename="style.jpg")

        async def load_service(_db, _tenant_id, _service_id):
            return service

        async def generate_available_slots(_db, **_kwargs):
            return [AvailableSlot(start_time=start_time, end_time=end_time, available_staff=(staff_id,))]

        async def choose_staff_with_fewest_bookings(_db, _tenant_id, staff_ids, _start_time):
            return staff_ids[0]

        async def lock_staff_for_booking(_db, _tenant_id, _staff_id, _service_id):
            return staff

        async def upsert_client(_db, _tenant_id, _payload):
            return client_id

        async def initialize_checkout_payment(**_kwargs):
            return (
                {"authorization_url": "https://checkout.paystack.com/test", "access_code": "access_test"},
                SimpleNamespace(provider="paystack", collection_mode="direct_split", platform_fee_amount=150, business_net_amount=2_850),
            )

        async def save_inspo_images(**kwargs):
            asset.booking_id = kwargs["booking_id"]
            return [asset]

        svc.load_service = load_service
        svc.generate_available_slots = generate_available_slots
        svc.choose_staff_with_fewest_bookings = choose_staff_with_fewest_bookings
        svc.lock_staff_for_booking = lock_staff_for_booking
        svc.upsert_client = upsert_client
        svc.initialize_checkout_payment = initialize_checkout_payment
        svc.save_inspo_images = save_inspo_images

        db = FakeBookingSession()
        await svc.create_public_booking(
            db,
            tenant=tenant,
            slug="ada-hair",
            payload=PublicBookingCreateRequest(
                service_id=service_id,
                staff_id=None,
                start_time=start_time,
                client={"full_name": "Chioma Okafor", "email": "chioma@example.com"},
            ),
            inspo_images=[SimpleNamespace(filename="style.jpg")],
        )

        booking = db.added[0]
        self.assertIn(asset, db.added)
        self.assertEqual(asset.booking_id, booking.id)
