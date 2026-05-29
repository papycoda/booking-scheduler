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

from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402

from app.dependencies import get_current_user  # noqa: E402
from app.services.auth_service import create_access_token  # noqa: E402


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, user):
        self.user = user
        self.statements = []

    async def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        if params and "tenant_id" in params:
            return FakeScalarResult(None)
        return FakeScalarResult(self.user)


class DependenciesTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_current_user_sets_tenant_context_before_user_lookup(self):
        tenant_id = uuid4()
        user = SimpleNamespace(id=uuid4(), tenant_id=tenant_id, role="tenant_owner", is_active=True)
        token = create_access_token(user)
        db = FakeSession(user)

        current_user = await get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            db,
        )

        self.assertEqual(current_user, user)
        self.assertEqual(db.statements[0][1], {"tenant_id": str(tenant_id)})
        self.assertIn("set_config('app.current_tenant_id'", db.statements[0][0])
