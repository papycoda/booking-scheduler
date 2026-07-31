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
from app.services.payment_provider import build_payment_plan, initialize_checkout_payment  # noqa: E402


class PaymentProviderTests(unittest.TestCase):
    def setUp(self):
        self.original_demo_mode = settings.demo_mode
        self.original_demo_admin_emails = settings.demo_admin_emails

    def tearDown(self):
        settings.demo_mode = self.original_demo_mode
        settings.demo_admin_emails = self.original_demo_admin_emails

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

    def test_authorized_demo_email_gets_local_payment_page(self):
        settings.demo_mode = True
        settings.demo_admin_emails = "demo@example.com"
        tenant = SimpleNamespace(
            payment_setup_status="not_started",
            paystack_subaccount_code=None,
            platform_fee_percentage=0,
        )

        data, _plan = __import__("asyncio").run(
            initialize_checkout_payment(
                email="DEMO@EXAMPLE.COM",
                amount=5_000,
                reference="bk_demo_reference",
                tenant=tenant,
                callback_url="http://localhost:3000/book/demo/verify",
                metadata={"booking_id": "demo"},
            )
        )

        self.assertIn("/demo/pay?", data["authorization_url"])
        self.assertTrue(data["access_code"].startswith("demo_access_"))
