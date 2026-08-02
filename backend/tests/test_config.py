import os
import unittest

from pydantic import ValidationError

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "")

from app.config import Settings  # noqa: E402


def make_settings(**overrides) -> Settings:
    values = {
        "secret_key": "s" * 48,
        "frontend_url": "http://localhost:3000",
        "environment": "development",
        "database_url": "postgresql+asyncpg://user:pass@localhost/db",
        "redis_url": "redis://localhost:6379",
        "paystack_secret_key": "",
        "demo_mode": True,
        "demo_admin_emails": "demo@example.com",
        "resend_api_key": None,
        "from_email": None,
        "twilio_account_sid": None,
        "twilio_auth_token": None,
        "twilio_whatsapp_from_number": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class SettingsTests(unittest.TestCase):
    def test_development_allows_demo_mode_without_external_providers(self):
        settings = make_settings()

        self.assertTrue(settings.demo_mode)
        self.assertEqual(settings.demo_admin_emails_list, ["demo@example.com"])

    def test_resend_configuration_must_be_complete(self):
        with self.assertRaisesRegex(ValidationError, "RESEND_API_KEY and FROM_EMAIL"):
            make_settings(resend_api_key="re_test")

    def test_twilio_configuration_must_be_complete(self):
        with self.assertRaisesRegex(ValidationError, "must be configured together"):
            make_settings(twilio_account_sid="AC123")

    def test_cloudinary_configuration_must_be_complete(self):
        with self.assertRaisesRegex(ValidationError, "must be configured together"):
            make_settings(cloudinary_cloud_name="demo")

    def test_cloudinary_provider_requires_credentials(self):
        with self.assertRaisesRegex(ValidationError, "Cloudinary credentials are required"):
            make_settings(image_storage_provider="cloudinary")

    def test_cloudinary_provider_accepts_complete_credentials(self):
        settings = make_settings(
            image_storage_provider="cloudinary",
            cloudinary_cloud_name="demo",
            cloudinary_api_key="key",
            cloudinary_api_secret="secret",
        )

        self.assertEqual(settings.image_storage_provider, "cloudinary")

    def test_production_rejects_demo_http_and_missing_providers(self):
        with self.assertRaises(ValidationError) as raised:
            make_settings(environment="production")

        message = str(raised.exception)
        self.assertIn("DEMO_MODE must be false", message)
        self.assertIn("FRONTEND_URL must use HTTPS", message)
        self.assertIn("PAYSTACK_SECRET_KEY is required", message)
        self.assertIn("RESEND_API_KEY and FROM_EMAIL are required", message)

    def test_production_accepts_complete_secure_configuration(self):
        settings = make_settings(
            environment="production",
            frontend_url="https://bookie.example.com",
            paystack_secret_key="sk_live_test",
            demo_mode=False,
            demo_admin_emails="",
            resend_api_key="re_test",
            from_email="Bookie <bookings@example.com>",
        )

        self.assertEqual(settings.environment, "production")
        self.assertFalse(settings.demo_mode)
