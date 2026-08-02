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
from app.services.image_storage import ImageStorageError, StoredImage  # noqa: E402
from app.services.inspo_service import save_inspo_images, signed_inspo_url, verify_inspo_signature  # noqa: E402

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


class FakeCloudStorage:
    provider = "cloudinary"

    def __init__(self, *, fail_on_call: int | None = None) -> None:
        self.fail_on_call = fail_on_call
        self.calls = 0
        self.deleted: list[str] = []

    async def store(self, **kwargs) -> StoredImage:
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise ImageStorageError("failed")
        return StoredImage(provider="cloudinary", key=kwargs["object_id"], format="jpg", data=None)

    async def delete(self, *, key: str | None) -> None:
        if key:
            self.deleted.append(key)


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
        self.assertEqual(asset.storage_provider, "database")
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

    async def test_cloudinary_storage_keeps_only_provider_metadata(self):
        storage = FakeCloudStorage()
        assets = await save_inspo_images(
            tenant_id=uuid4(),
            booking_id=uuid4(),
            slug="tenant-slug",
            files=[FakeUploadFile("style.jpg", "image/jpeg", JPEG_BYTES)],
            storage=storage,
        )

        self.assertEqual(assets[0].storage_provider, "cloudinary")
        self.assertIsNotNone(assets[0].storage_key)
        self.assertEqual(assets[0].storage_format, "jpg")
        self.assertIsNone(assets[0].data)

    async def test_partial_cloudinary_failure_cleans_up_completed_uploads(self):
        storage = FakeCloudStorage(fail_on_call=2)

        with self.assertRaises(Exception) as raised:
            await save_inspo_images(
                tenant_id=uuid4(),
                booking_id=uuid4(),
                slug="tenant-slug",
                files=[
                    FakeUploadFile("one.jpg", "image/jpeg", JPEG_BYTES),
                    FakeUploadFile("two.jpg", "image/jpeg", JPEG_BYTES),
                ],
                storage=storage,
            )

        self.assertEqual(getattr(raised.exception, "status_code", None), 502)
        self.assertEqual(len(storage.deleted), 1)

    def test_signed_inspo_url_is_tenant_scoped_and_expires(self):
        tenant_id = uuid4()
        asset = type("Asset", (), {
            "tenant_id": tenant_id,
            "stored_filename": "stored-id",
            "url": "/book/tenant-slug/inspo/stored-id",
        })()

        signed_url = signed_inspo_url(asset, ttl_seconds=60)
        query = signed_url.split("?", 1)[1]
        values = dict(part.split("=", 1) for part in query.split("&"))

        self.assertTrue(
            verify_inspo_signature(
                tenant_id=tenant_id,
                stored_filename="stored-id",
                expires=int(values["expires"]),
                signature=values["signature"],
            )
        )
        self.assertFalse(
            verify_inspo_signature(
                tenant_id=uuid4(),
                stored_filename="stored-id",
                expires=int(values["expires"]),
                signature=values["signature"],
            )
        )
