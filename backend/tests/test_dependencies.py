import os
import unittest
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.dependencies import require_tenant_owner  # noqa: E402


class DependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_require_tenant_owner_allows_owner(self):
        user = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), role="tenant_owner")

        self.assertIs(await require_tenant_owner(user), user)

    async def test_require_tenant_owner_rejects_staff(self):
        user = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), role="tenant_staff")

        with self.assertRaises(Exception) as raised:
            await require_tenant_owner(user)

        self.assertEqual(getattr(raised.exception, "status_code", None), 403)
        self.assertEqual(raised.exception.detail["error"], "INSUFFICIENT_ROLE")
