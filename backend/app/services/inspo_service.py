import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import urlencode
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.models.booking import BookingInspoAsset
from app.services.image_storage import ImageStorageError, get_image_storage

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class ValidatedImage:
    filename: str
    content_type: str
    content: bytes


def content_matches_declared_image_type(content_type: str, content: bytes) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False


async def validate_inspo_images(files: list[UploadFile]) -> list[ValidatedImage]:
    if len(files) > settings.max_inspo_images:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "TOO_MANY_INSPO_IMAGES", "message": f"Upload up to {settings.max_inspo_images} inspiration images."},
        )

    total_size = 0
    validated: list[ValidatedImage] = []

    for file in files:
        content_type = file.content_type or ""
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"error": "INVALID_INSPO_IMAGE", "message": "Upload JPEG, PNG, or WebP inspiration images."},
            )

        content = await file.read()
        if not content_matches_declared_image_type(content_type, content):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"error": "INVALID_INSPO_IMAGE", "message": "Uploaded image bytes do not match the declared file type."},
            )

        size = len(content)
        total_size += size
        if size > settings.max_inspo_image_bytes or total_size > settings.max_inspo_total_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"error": "INSPO_IMAGE_TOO_LARGE", "message": "One or more inspiration images are too large."},
            )

        validated.append(
            ValidatedImage(
                filename=file.filename or "image",
                content_type=content_type,
                content=content,
            )
        )
    return validated


async def save_inspo_images(
    *,
    tenant_id: UUID,
    booking_id: UUID,
    slug: str,
    files: list[UploadFile],
    storage=None,
) -> list[BookingInspoAsset]:
    validated = await validate_inspo_images(files)
    image_storage = storage or get_image_storage()
    assets: list[BookingInspoAsset] = []
    stored_keys: list[str] = []
    try:
        for image in validated:
            stored_filename = str(uuid4())
            stored = await image_storage.store(
                tenant_id=str(tenant_id),
                booking_id=str(booking_id),
                object_id=stored_filename,
                filename=image.filename,
                content_type=image.content_type,
                content=image.content,
            )
            if stored.key:
                stored_keys.append(stored.key)
            assets.append(
                BookingInspoAsset(
                    booking_id=booking_id,
                    tenant_id=tenant_id,
                    original_filename=image.filename,
                    stored_filename=stored_filename,
                    content_type=image.content_type,
                    size_bytes=len(image.content),
                    url=f"/book/{slug}/inspo/{stored_filename}",
                    data=stored.data,
                    storage_provider=stored.provider,
                    storage_key=stored.key,
                    storage_format=stored.format,
                )
            )
    except ImageStorageError as exc:
        for key in stored_keys:
            try:
                await image_storage.delete(key=key)
            except ImageStorageError:
                pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "INSPO_STORAGE_UNAVAILABLE", "message": "Images could not be saved right now. Please try again."},
        ) from exc

    return assets


def signed_inspo_url(asset: BookingInspoAsset, *, ttl_seconds: int = 3600) -> str:
    expires = int(time.time()) + ttl_seconds
    payload = f"{asset.tenant_id}:{asset.stored_filename}:{expires}"
    signature = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{asset.url}?{urlencode({'expires': expires, 'signature': signature})}"


def verify_inspo_signature(*, tenant_id: UUID, stored_filename: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    payload = f"{tenant_id}:{stored_filename}:{expires}"
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
