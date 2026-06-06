import os
import unittest
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.config import settings  # noqa: E402
from app.services.inspo_service import save_inspo_images  # noqa: E402

JPEG_BYTES = b"\xff\xd8\xff\xe0image-bytes"
PNG_BYTES = b"\x89PNG\r\n\x1a\nimage-bytes"
WEBP_BYTES = b"RIFF\x10\x00\x00\x00WEBPimage-bytes"


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.content = content

    async def read(self) -> bytes:
        return self.content


class InspoServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_inspo_images_rejects_non_images(self):
        with self.assertRaises(Exception) as raised:
            await save_inspo_images(
                tenant_id=uuid4(),
                booking_id=uuid4(),
                slug="tenant-slug",
                files=[FakeUploadFile("notes.txt", "text/plain", b"not image")],
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 415)

    async def test_save_inspo_images_stores_metadata_and_bytes(self):
        tenant_id = uuid4()
        booking_id = uuid4()
        assets = await save_inspo_images(
            tenant_id=tenant_id,
            booking_id=booking_id,
            slug="tenant-slug",
            files=[FakeUploadFile("style.jpg", "image/jpeg", JPEG_BYTES)],
        )

        asset = assets[0]
        self.assertEqual(asset.tenant_id, tenant_id)
        self.assertEqual(asset.booking_id, booking_id)
        self.assertEqual(asset.original_filename, "style.jpg")
        self.assertEqual(asset.content_type, "image/jpeg")
        self.assertEqual(asset.size_bytes, len(JPEG_BYTES))
        self.assertEqual(asset.data, JPEG_BYTES)
        self.assertTrue(asset.url.startswith("/book/tenant-slug/inspo/"))

    async def test_save_inspo_images_rejects_svg(self):
        with self.assertRaises(Exception) as raised:
            await save_inspo_images(
                tenant_id=uuid4(),
                booking_id=uuid4(),
                slug="tenant-slug",
                files=[FakeUploadFile("style.svg", "image/svg+xml", b"<svg></svg>")],
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 415)

    async def test_save_inspo_images_rejects_mismatched_magic_bytes(self):
        with self.assertRaises(Exception) as raised:
            await save_inspo_images(
                tenant_id=uuid4(),
                booking_id=uuid4(),
                slug="tenant-slug",
                files=[FakeUploadFile("style.jpg", "image/jpeg", PNG_BYTES)],
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 415)

    async def test_save_inspo_images_accepts_png_and_webp(self):
        assets = await save_inspo_images(
            tenant_id=uuid4(),
            booking_id=uuid4(),
            slug="tenant-slug",
            files=[
                FakeUploadFile("style.png", "image/png", PNG_BYTES),
                FakeUploadFile("style.webp", "image/webp", WEBP_BYTES),
            ],
        )

        self.assertEqual([asset.content_type for asset in assets], ["image/png", "image/webp"])
