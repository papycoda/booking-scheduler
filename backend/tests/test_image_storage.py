import hashlib
import os
import unittest
from urllib.parse import parse_qs, urlparse

import httpx

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.services.image_storage import CloudinaryImageStorage, ImageStorageError, cloudinary_signature  # noqa: E402


class CloudinaryImageStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_is_signed_and_uses_authenticated_delivery(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            body = request.content
            self.assertEqual(str(request.url), "https://api.cloudinary.com/v1_1/demo/image/upload")
            self.assertIn(b'name="type"', body)
            self.assertIn(b"authenticated", body)
            self.assertIn(b'name="signature"', body)
            self.assertNotIn(b"api-secret", body)
            return httpx.Response(200, json={"public_id": "object-id", "format": "jpg", "type": "authenticated"})

        storage = CloudinaryImageStorage(
            cloud_name="demo",
            api_key="api-key",
            api_secret="api-secret",
            transport=httpx.MockTransport(handler),
        )

        stored = await storage.store(
            tenant_id="tenant",
            booking_id="booking",
            object_id="object-id",
            filename="style.jpg",
            content_type="image/jpeg",
            content=b"image",
        )

        self.assertEqual(stored.provider, "cloudinary")
        self.assertEqual(stored.key, "object-id")
        self.assertIsNone(stored.data)

    async def test_upload_rejects_malformed_provider_response(self):
        storage = CloudinaryImageStorage(
            cloud_name="demo",
            api_key="api-key",
            api_secret="api-secret",
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"type": "upload"})),
        )

        with self.assertRaises(ImageStorageError):
            await storage.store(
                tenant_id="tenant",
                booking_id="booking",
                object_id="object-id",
                filename="style.jpg",
                content_type="image/jpeg",
                content=b"image",
            )

    def test_private_download_url_is_short_lived_and_signed(self):
        storage = CloudinaryImageStorage(cloud_name="demo", api_key="api-key", api_secret="api-secret")
        url = storage.private_download_url(key="object-id", image_format="jpg", expires_at=2_000_000_000)
        parsed = urlparse(url)
        query = {key: value[0] for key, value in parse_qs(parsed.query).items()}
        signed_parameters = {key: query[key] for key in ("expires_at", "format", "public_id", "timestamp", "type")}

        self.assertEqual(parsed.path, "/v1_1/demo/image/download")
        self.assertEqual(query["type"], "authenticated")
        self.assertEqual(query["signature"], cloudinary_signature(signed_parameters, "api-secret"))
        self.assertNotIn("api-secret", url)

    def test_cloudinary_signature_matches_documented_sorting(self):
        parameters = {"timestamp": 1315060510, "public_id": "sample"}
        expected = hashlib.sha1(b"public_id=sample&timestamp=1315060510secret").hexdigest()

        self.assertEqual(cloudinary_signature(parameters, "secret"), expected)
