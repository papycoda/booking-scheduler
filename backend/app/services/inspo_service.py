from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.models.booking import BookingInspoAsset

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def content_matches_declared_image_type(content_type: str, content: bytes) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False


async def save_inspo_images(*, tenant_id: UUID, booking_id: UUID, slug: str, files: list[UploadFile]) -> list[BookingInspoAsset]:
    if len(files) > settings.max_inspo_images:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "TOO_MANY_INSPO_IMAGES", "message": f"Upload up to {settings.max_inspo_images} inspiration images."},
        )

    total_size = 0
    assets: list[BookingInspoAsset] = []

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

        stored_filename = str(uuid4())
        assets.append(
            BookingInspoAsset(
                booking_id=booking_id,
                tenant_id=tenant_id,
                original_filename=file.filename or "image",
                stored_filename=stored_filename,
                content_type=content_type,
                size_bytes=size,
                url=f"/book/{slug}/inspo/{stored_filename}",
                data=content,
            )
        )

    return assets
