import os
import unittest

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


class ErrorResponseTests(unittest.TestCase):
    def test_validation_error_is_structured(self):
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/register", json={})

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(set(body.keys()), {"error", "message"})
        self.assertEqual(body["error"], "VALIDATION_ERROR")

    def test_missing_auth_error_is_structured(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/tenants/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "NOT_AUTHENTICATED", "message": "Missing bearer token."})
