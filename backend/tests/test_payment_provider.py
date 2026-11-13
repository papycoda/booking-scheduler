import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.config import settings  # noqa: E402
from app.services import payment_provider  # noqa: E402
from app.services.payment_provider import build_payment_plan, initialize_checkout_payment  # noqa: E402


class PaymentProviderTests(unittest.TestCase):
    def test_platform_collected_without_split_setup_caps_platform_fee(self):
        tenant = SimpleNamespace(
            payment_setup_status="not_started",
            paystack_subaccount_code=None,
            platform_fee_percentage=25,
        )

        plan = build_payment_plan(tenant, 20_000)

        self.assertEqual(plan.collection_mode, "platform_collected")
        self.assertIsNone(plan.subaccount)
        self.assertEqual(plan.platform_fee_amount, 2_000)
        self.assertEqual(plan.business_net_amount, 18_000)
        self.assertEqual(plan.transaction_charge, 0)

    def test_platform_fee_is_ten_percent_capped_at_five_thousand_naira(self):
        tenant = SimpleNamespace(
            payment_setup_status="not_started",
            paystack_subaccount_code=None,
            platform_fee_percentage=30,
        )

        plan = build_payment_plan(tenant, 10_000_000)

        self.assertEqual(plan.platform_fee_amount, 500_000)
        self.assertEqual(plan.business_net_amount, 9_500_000)

    def test_split_ready_uses_subaccount_and_platform_fee_as_transaction_charge(self):
        tenant = SimpleNamespace(
            payment_setup_status="split_ready",
            paystack_subaccount_code="ACCT_test",
            platform_fee_percentage=7.5,
        )

        plan = build_payment_plan(tenant, 40_000)

        self.assertEqual(plan.collection_mode, "direct_split")
        self.assertEqual(plan.subaccount, "ACCT_test")
        self.assertEqual(plan.platform_fee_amount, 3_000)
        self.assertEqual(plan.business_net_amount, 37_000)
        self.assertEqual(plan.transaction_charge, 3_000)
        self.assertEqual(plan.bearer, "subaccount")


class DemoCheckoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_demo_mode = settings.demo_mode
        self.original_demo_admin_emails = settings.demo_admin_emails
        self.original_initialize_transaction = payment_provider.initialize_transaction
        settings.demo_mode = True
        settings.demo_admin_emails = "admin@example.com"

    def tearDown(self) -> None:
        settings.demo_mode = self.original_demo_mode
        settings.demo_admin_emails = self.original_demo_admin_emails
        payment_provider.initialize_transaction = self.original_initialize_transaction

    async def test_customer_email_does_not_select_demo_checkout(self):
        calls = []

        async def initialize_transaction(**kwargs):
            calls.append(kwargs)
            return {"authorization_url": "https://checkout.paystack.com/real", "access_code": "real_access"}

        payment_provider.initialize_transaction = initialize_transaction
        tenant = SimpleNamespace(payment_setup_status="not_started", paystack_subaccount_code=None, platform_fee_percentage=5)

        data, _plan = await initialize_checkout_payment(
            email="admin@example.com",
            amount=1_000,
            reference="bk_reference",
            tenant=tenant,
            callback_url="http://localhost:3000/book/ada/verify",
            metadata={"booking_id": "booking"},
        )

        self.assertEqual(data["authorization_url"], "https://checkout.paystack.com/real")
        self.assertEqual(calls[0]["email"], "admin@example.com")

    async def test_authenticated_demo_admin_selects_demo_checkout(self):
        async def initialize_transaction(**_kwargs):
            raise AssertionError("demo admin checkout should not call Paystack")

        payment_provider.initialize_transaction = initialize_transaction
        tenant = SimpleNamespace(payment_setup_status="not_started", paystack_subaccount_code=None, platform_fee_percentage=5)

        data, _plan = await initialize_checkout_payment(
            email="customer@example.com",
            amount=1_000,
            reference="bk_reference",
            tenant=tenant,
            callback_url="http://localhost:3000/book/ada/verify",
            metadata={"booking_id": "booking"},
            actor_email="admin@example.com",
        )

        self.assertIn("/demo/pay?", data["authorization_url"])
        self.assertTrue(data["access_code"].startswith("demo_access_"))
