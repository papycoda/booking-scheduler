import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_x")

from app.config import settings  # noqa: E402
from app.services.inspo_service import save_inspo_images  # noqa: E402


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.content = content

    async def read(self) -> bytes:
        return self.content


class InspoServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_inspo_images_rejects_non_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_dir = settings.upload_dir
            settings.upload_dir = temp_dir
            try:
                with self.assertRaises(Exception) as raised:
                    await save_inspo_images(
                        tenant_id=uuid4(),
                        booking_id=uuid4(),
                        files=[FakeUploadFile("notes.txt", "text/plain", b"not image")],
                    )
            finally:
                settings.upload_dir = original_dir

        self.assertEqual(getattr(raised.exception, "status_code", None), 415)

    async def test_save_inspo_images_stores_metadata_and_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_dir = settings.upload_dir
            original_base_url = settings.upload_base_url
            settings.upload_dir = temp_dir
            settings.upload_base_url = "/uploads"
            tenant_id = uuid4()
            booking_id = uuid4()
            try:
                assets = await save_inspo_images(
                    tenant_id=tenant_id,
                    booking_id=booking_id,
                    files=[FakeUploadFile("style.jpg", "image/jpeg", b"image-bytes")],
                )
                stored_path_exists = Path(temp_dir, str(tenant_id), str(booking_id), assets[0].stored_filename).exists()
            finally:
                settings.upload_dir = original_dir
                settings.upload_base_url = original_base_url

        asset = assets[0]
        self.assertEqual(asset.tenant_id, tenant_id)
        self.assertEqual(asset.booking_id, booking_id)
        self.assertEqual(asset.original_filename, "style.jpg")
        self.assertEqual(asset.content_type, "image/jpeg")
        self.assertEqual(asset.size_bytes, len(b"image-bytes"))
        self.assertTrue(asset.url.startswith(f"/uploads/{tenant_id}/{booking_id}/"))
        self.assertTrue(stored_path_exists)
