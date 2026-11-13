import os
import unittest

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.config import normalize_async_database_url  # noqa: E402


class DatabaseUrlTests(unittest.TestCase):
    def test_render_postgres_url_uses_asyncpg_and_ssl(self):
        url, connect_args = normalize_async_database_url(
            "postgres://booking_scheduler:secret@dpg-api/booking_scheduler?sslmode=require"
        )

        self.assertTrue(url.startswith("postgresql+asyncpg://"))
        self.assertNotIn("sslmode", url)
        self.assertEqual(connect_args, {"ssl": True})

    def test_existing_asyncpg_url_stays_plain(self):
        url, connect_args = normalize_async_database_url("postgresql+asyncpg://user:pass@localhost/db")

        self.assertEqual(url, "postgresql+asyncpg://user:pass@localhost/db")
        self.assertEqual(connect_args, {})
