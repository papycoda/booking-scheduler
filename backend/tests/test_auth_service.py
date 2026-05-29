import os
import unittest
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.services import auth_service  # noqa: E402
from jose import jwt  # noqa: E402


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)


class AuthServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_redis = auth_service.redis_client
        self.fake_redis = FakeRedis()
        auth_service.redis_client = self.fake_redis

    def tearDown(self) -> None:
        auth_service.redis_client = self.original_redis

    async def test_password_reset_token_is_hmac_stored_and_single_use(self):
        user_id = uuid4()
        token = await auth_service.create_password_reset_token(type("User", (), {"id": user_id})())

        self.assertNotIn(token, "".join(self.fake_redis.values.keys()))
        self.assertEqual(await auth_service.consume_password_reset_token(token), user_id)
        self.assertIsNone(await auth_service.consume_password_reset_token(token))

    def test_hmac_reset_token_is_deterministic_without_exposing_plaintext(self):
        digest = auth_service.hmac_reset_token("secret-token")

        self.assertEqual(digest, auth_service.hmac_reset_token("secret-token"))
        self.assertNotEqual(digest, "secret-token")

    def test_access_and_refresh_tokens_have_expected_claim_types(self):
        user = type("User", (), {"id": uuid4(), "tenant_id": uuid4(), "role": "tenant_owner"})()

        access_payload = jwt.decode(auth_service.create_access_token(user), auth_service.settings.secret_key, algorithms=["HS256"])
        refresh_payload = jwt.decode(auth_service.create_refresh_token(user), auth_service.settings.secret_key, algorithms=["HS256"])

        self.assertEqual(access_payload["type"], "access")
        self.assertEqual(refresh_payload["type"], "refresh")
        self.assertEqual(access_payload["tenant_id"], str(user.tenant_id))
        self.assertEqual(refresh_payload["role"], "tenant_owner")
