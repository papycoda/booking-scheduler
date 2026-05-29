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

from fastapi import Response  # noqa: E402

from app.routers import auth as auth_router  # noqa: E402
from app.schemas.auth import RegisterRequest  # noqa: E402


class FakeRegisterSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()

    async def commit(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, _item):
        return None


class AuthRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.originals = {
            "get_user_by_email": auth_router.get_user_by_email,
            "generate_unique_slug": auth_router.generate_unique_slug,
            "hash_password": auth_router.hash_password,
            "create_access_token": auth_router.create_access_token,
            "create_refresh_token": auth_router.create_refresh_token,
        }

    def tearDown(self) -> None:
        for name, original in self.originals.items():
            setattr(auth_router, name, original)

    async def test_register_creates_tenant_owner_and_sets_refresh_cookie(self):
        async def get_user_by_email(_db, _email):
            return None

        async def generate_unique_slug(_db, business_name):
            self.assertEqual(business_name, "Ada Hair Studio")
            return "ada-hair-studio"

        auth_router.get_user_by_email = get_user_by_email
        auth_router.generate_unique_slug = generate_unique_slug
        auth_router.hash_password = lambda password: f"hashed:{password}"
        auth_router.create_access_token = lambda _user: "access-token"
        auth_router.create_refresh_token = lambda _user: "refresh-token"

        response = Response()
        db = FakeRegisterSession()
        result = await auth_router.register.__wrapped__(
            SimpleNamespace(),
            RegisterRequest(
                business_name="Ada Hair Studio",
                full_name="Ada Okafor",
                email="ADA@example.com",
                password="strong-password",
            ),
            response,
            db,
        )

        tenant, user = db.added
        self.assertTrue(db.committed)
        self.assertFalse(db.rolled_back)
        self.assertEqual(tenant.slug, "ada-hair-studio")
        self.assertEqual(user.tenant_id, tenant.id)
        self.assertEqual(user.email, "ada@example.com")
        self.assertEqual(user.hashed_password, "hashed:strong-password")
        self.assertEqual(user.role, "tenant_owner")
        self.assertEqual(result.access_token, "access-token")
        self.assertEqual(result.tenant_id, tenant.id)
        self.assertEqual(result.slug, "ada-hair-studio")
        self.assertIn("refresh_token=refresh-token", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=strict", response.headers["set-cookie"])
