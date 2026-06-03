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
from app.schemas.tenant import (  # noqa: E402
    PayoutSetupRequest,
    PaystackOnboardingRequest,
    PaystackStatusResponse,
    TenantResponse,
    TenantUpdateRequest,
)
from app.services.paystack_service import PaystackError  # noqa: E402
from app.services.settlement_service import mask_account_number  # noqa: E402


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeTenantSession:
    def __init__(self, tenant, conflict_id=None):
        self.tenant = tenant
        self.conflict_id = conflict_id
        self.committed = False
        self.refreshed = False
        self.execute_count = 0

    async def execute(self, _stmt):
        self.execute_count += 1
        if self.execute_count == 2:
            return FakeScalarResult(self.conflict_id)
        return FakeScalarResult(self.tenant)

    async def commit(self):
        self.committed = True

    async def refresh(self, _tenant):
        self.refreshed = True


class TenantRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_create_subaccount = tenant_router.create_subaccount
        self.original_create_transfer_recipient = tenant_router.create_transfer_recipient
        self.original_resolve_bank_code = tenant_router.resolve_bank_code

    def tearDown(self) -> None:
        tenant_router.create_subaccount = self.original_create_subaccount
        tenant_router.create_transfer_recipient = self.original_create_transfer_recipient
        tenant_router.resolve_bank_code = self.original_resolve_bank_code

    async def test_update_current_tenant_allows_available_custom_slug(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            slug="ada-hair",
            name="Ada Hair",
        )
        db = FakeTenantSession(tenant)

        response = await tenant_router.update_current_tenant(
            TenantUpdateRequest(slug="Ada Hair Prime", name="Ada Hair Prime"),
            SimpleNamespace(tenant_id=tenant.id),
            db,
        )

        self.assertTrue(db.committed)
        self.assertTrue(db.refreshed)
        self.assertEqual(response.slug, "ada-hair-prime")
        self.assertEqual(response.name, "Ada Hair Prime")

    async def test_update_current_tenant_rejects_taken_slug(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            slug="ada-hair",
            name="Ada Hair",
        )

        with self.assertRaises(Exception) as raised:
            await tenant_router.update_current_tenant(
                TenantUpdateRequest(slug="Taken Slug"),
                SimpleNamespace(tenant_id=tenant.id),
                FakeTenantSession(tenant, conflict_id=uuid4()),
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 409)
        self.assertEqual(raised.exception.detail["error"], "SLUG_UNAVAILABLE")
        self.assertEqual(tenant.slug, "ada-hair")

    async def test_onboard_paystack_stores_subaccount_on_current_tenant(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            platform_fee_percentage=Decimal("5.00"),
            paystack_subaccount_code=None,
            paystack_business_name=None,
            payout_bank_code=None,
            payout_account_number=None,
            payout_account_name=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
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
        self.assertEqual(tenant.payment_setup_status, "split_ready")
        self.assertTrue(response.onboarded)

    async def test_onboard_paystack_maps_paystack_failure_to_502(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            platform_fee_percentage=Decimal("5.00"),
            paystack_subaccount_code=None,
            paystack_business_name=None,
            payout_bank_code=None,
            payout_account_number=None,
            payout_account_name=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
        )

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

    async def test_save_payout_setup_accepts_bank_details_without_subaccount(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_code=None,
            payout_account_number=None,
            payout_account_name=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
        )

        async def create_transfer_recipient(**_kwargs):
            return {"recipient_code": "RCP_test"}

        tenant_router.create_transfer_recipient = create_transfer_recipient
        db = FakeTenantSession(tenant)

        response = await tenant_router.save_payout_setup(
            PayoutSetupRequest(
                bank_code="058",
                account_number="0123456789",
                account_name="Ada Hair Ltd",
            ),
            SimpleNamespace(tenant_id=tenant.id),
            db,
        )

        self.assertTrue(db.committed)
        self.assertEqual(tenant.payout_bank_code, "058")
        self.assertEqual(tenant.payout_account_number, "0123456789")
        self.assertEqual(tenant.payout_account_name, "Ada Hair Ltd")
        self.assertEqual(tenant.payout_recipient_code, "RCP_test")
        self.assertEqual(tenant.payment_setup_status, "bank_added")
        self.assertTrue(response.payments_enabled)
        self.assertTrue(response.payout_ready)

    async def test_save_payout_setup_accepts_bank_name_and_stores_provider_code(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_code=None,
            payout_bank_name=None,
            payout_account_number=None,
            payout_account_name=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
        )
        captured = {}

        async def resolve_bank_code(bank_name):
            self.assertEqual(bank_name, "GTBank")
            return ("058", "GTBank")

        async def create_transfer_recipient(**kwargs):
            captured.update(kwargs)
            return {"recipient_code": "RCP_test"}

        tenant_router.resolve_bank_code = resolve_bank_code
        tenant_router.create_transfer_recipient = create_transfer_recipient

        response = await tenant_router.save_payout_setup(
            PayoutSetupRequest(
                bank_name="GTBank",
                account_number="0123456789",
                account_name="Ada Hair Ltd",
            ),
            SimpleNamespace(tenant_id=tenant.id),
            FakeTenantSession(tenant),
        )

        self.assertEqual(captured["bank_code"], "058")
        self.assertEqual(tenant.payout_bank_code, "058")
        self.assertEqual(tenant.payout_bank_name, "GTBank")
        self.assertEqual(response.payout_bank_name, "GTBank")
        self.assertTrue(response.payout_ready)

    async def test_save_payout_setup_failure_saves_details_but_blocks_payouts(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_code=None,
            payout_bank_name=None,
            payout_account_number=None,
            payout_account_name=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
        )

        async def resolve_bank_code(_bank_name):
            return ("058", "GTBank")

        async def create_transfer_recipient(**_kwargs):
            raise PaystackError("failed")

        tenant_router.resolve_bank_code = resolve_bank_code
        tenant_router.create_transfer_recipient = create_transfer_recipient

        response = await tenant_router.save_payout_setup(
            PayoutSetupRequest(
                bank_name="GTBank",
                account_number="0123456789",
                account_name="Ada Hair Ltd",
            ),
            SimpleNamespace(tenant_id=tenant.id),
            FakeTenantSession(tenant),
        )

        self.assertEqual(tenant.payout_bank_name, "GTBank")
        self.assertIsNone(tenant.payout_recipient_code)
        self.assertEqual(tenant.payment_setup_status, "verification_failed")
        self.assertFalse(response.payout_ready)
        self.assertEqual(
            response.warning_message,
            "We saved your details, but could not verify this payout account yet. Please check the bank name and account number."
        )

    async def test_paystack_status_masks_account_number(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_name="GTBank",
            payout_account_name="Ada Hair Ltd",
            payout_account_number="0123456789",
            payout_recipient_code="RCP_test",
            payment_setup_status="bank_added",
        )

        response = tenant_router.tenant_payment_status(tenant)

        # Field serializer applies on serialization (model_dump), not direct access
        response_dict = response.model_dump()
        self.assertEqual(response_dict["masked_payout_account_number"], "******6789")

    async def test_paystack_status_masks_account_number_with_none(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_name=None,
            payout_account_name=None,
            payout_account_number=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
        )

        response = tenant_router.tenant_payment_status(tenant)

        self.assertIsNone(response.masked_payout_account_number)

    async def test_paystack_status_does_not_return_provider_codes(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_name="GTBank",
            payout_account_name="Ada Hair Ltd",
            payout_account_number="0123456789",
            payout_recipient_code="RCP_test",
            paystack_subaccount_code="ACCT_test",
            payment_setup_status="split_ready",
        )

        response = tenant_router.tenant_payment_status(tenant)

        # PaystackStatusResponse should not have these fields
        self.assertFalse(hasattr(response, "paystack_subaccount_code"))
        self.assertFalse(hasattr(response, "payout_recipient_code"))

    async def test_paystack_status_includes_warning_message(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_name="GTBank",
            payout_account_name="Ada Hair Ltd",
            payout_account_number="0123456789",
            payout_recipient_code=None,
            payment_setup_status="verification_failed",
        )

        warning = "We saved your details, but could not verify this payout account yet. Please check the bank name and account number."
        response = tenant_router.tenant_payment_status(tenant, warning_message=warning)

        self.assertEqual(response.warning_message, warning)
        self.assertFalse(response.payout_ready)

    async def test_tenant_response_masks_account_number(self):
        tenant_dict = {
            "id": uuid4(),
            "slug": "ada-hair",
            "name": "Ada Hair",
            "description": None,
            "logo_url": None,
            "timezone": "Africa/Lagos",
            "phone": None,
            "address": None,
            "payout_bank_name": "GTBank",
            "payout_account_name": "Ada Hair Ltd",
            "payment_setup_status": "bank_added",
            "platform_fee_percentage": Decimal("5.00"),
            "allow_staff_selection": True,
            "booking_buffer_minutes": 15,
            "default_deposit_amount": 1000,
            "advance_booking_days": 30,
            "min_notice_hours": 2,
            "cancellation_notice_hours": 24,
            "status": "active",
            "masked_payout_account_number": "0123456789",  # Raw account number passed in
        }

        response = TenantResponse(**tenant_dict)

        # Field serializer applies on serialization (model_dump), not direct access
        response_dict = response.model_dump()
        self.assertEqual(response_dict["masked_payout_account_number"], "******6789")

    async def test_tenant_response_handles_none_account_number(self):
        tenant_dict = {
            "id": uuid4(),
            "slug": "ada-hair",
            "name": "Ada Hair",
            "description": None,
            "logo_url": None,
            "timezone": "Africa/Lagos",
            "phone": None,
            "address": None,
            "payout_bank_name": None,
            "payout_account_name": None,
            "payment_setup_status": "not_started",
            "platform_fee_percentage": Decimal("5.00"),
            "allow_staff_selection": True,
            "booking_buffer_minutes": 15,
            "default_deposit_amount": 1000,
            "advance_booking_days": 30,
            "min_notice_hours": 2,
            "cancellation_notice_hours": 24,
            "status": "active",
            "masked_payout_account_number": None,
        }

        response = TenantResponse(**tenant_dict)

        self.assertIsNone(response.masked_payout_account_number)

    async def test_payout_setup_verification_failed_returns_warning(self):
        tenant = SimpleNamespace(
            id=uuid4(),
            payout_bank_code=None,
            payout_bank_name=None,
            payout_account_number=None,
            payout_account_name=None,
            payout_recipient_code=None,
            payment_setup_status="not_started",
        )

        async def resolve_bank_code(_bank_name):
            return ("058", "GTBank")

        async def create_transfer_recipient(**_kwargs):
            raise PaystackError("failed")

        tenant_router.resolve_bank_code = resolve_bank_code
        tenant_router.create_transfer_recipient = create_transfer_recipient

        response = await tenant_router.save_payout_setup(
            PayoutSetupRequest(
                bank_name="GTBank",
                account_number="0123456789",
                account_name="Ada Hair Ltd",
            ),
            SimpleNamespace(tenant_id=tenant.id),
            FakeTenantSession(tenant),
        )

        # Verify details were saved
        self.assertEqual(tenant.payout_bank_name, "GTBank")
        self.assertEqual(tenant.payout_account_number, "0123456789")
        self.assertEqual(tenant.payout_account_name, "Ada Hair Ltd")

        # Verify payout is blocked due to failed verification
        self.assertIsNone(tenant.payout_recipient_code)
        self.assertFalse(response.payout_ready)

        # Verify user-safe warning message is returned
        self.assertEqual(
            response.warning_message,
            "We saved your details, but could not verify this payout account yet. Please check the bank name and account number."
        )

        # Verify the account number is masked in serialized response
        response_dict = response.model_dump()
        self.assertEqual(response_dict["masked_payout_account_number"], "******6789")
