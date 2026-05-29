import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.routers import tenants as tenant_router  # noqa: E402
from app.schemas.tenant import PaystackOnboardingRequest  # noqa: E402
from app.services.paystack_service import PaystackError  # noqa: E402


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeTenantSession:
    def __init__(self, tenant):
        self.tenant = tenant
        self.committed = False

    async def execute(self, _stmt):
        return FakeScalarResult(self.tenant)

    async def commit(self):
        self.committed = True


class TenantRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_create_subaccount = tenant_router.create_subaccount

    def tearDown(self) -> None:
        tenant_router.create_subaccount = self.original_create_subaccount

    async def test_onboard_paystack_stores_subaccount_on_current_tenant(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            platform_fee_percentage=Decimal("5.00"),
            paystack_subaccount_code=None,
            paystack_business_name=None,
        )
        captured = {}

        async def create_subaccount(**kwargs):
            captured.update(kwargs)
            return {"subaccount_code": "ACCT_test"}

        tenant_router.create_subaccount = create_subaccount
        db = FakeTenantSession(tenant)

        response = await tenant_router.onboard_paystack(
            PaystackOnboardingRequest(
                business_name="Ada Hair",
                settlement_bank="058",
                account_number="0123456789",
            ),
            SimpleNamespace(tenant_id=tenant.id),
            db,
        )

        self.assertTrue(db.committed)
        self.assertEqual(captured["percentage_charge"], 5.0)
        self.assertEqual(tenant.paystack_subaccount_code, "ACCT_test")
        self.assertEqual(tenant.paystack_business_name, "Ada Hair")
        self.assertTrue(response.onboarded)

    async def test_onboard_paystack_maps_paystack_failure_to_502(self):
        tenant = SimpleNamespace(id=uuid4(), platform_fee_percentage=Decimal("5.00"))

        async def create_subaccount(**_kwargs):
            raise PaystackError("failed")

        tenant_router.create_subaccount = create_subaccount

        with self.assertRaises(Exception) as raised:
            await tenant_router.onboard_paystack(
                PaystackOnboardingRequest(
                    business_name="Ada Hair",
                    settlement_bank="058",
                    account_number="0123456789",
                ),
                SimpleNamespace(tenant_id=tenant.id),
                FakeTenantSession(tenant),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 502)
        self.assertEqual(raised.exception.detail["error"], "PAYSTACK_SUBACCOUNT_FAILED")
