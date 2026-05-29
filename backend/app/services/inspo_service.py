from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.models.booking import BookingInspoAsset


async def save_inspo_images(*, tenant_id: UUID, booking_id: UUID, files: list[UploadFile]) -> list[BookingInspoAsset]:
    if len(files) > settings.max_inspo_images:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "TOO_MANY_INSPO_IMAGES", "message": f"Upload up to {settings.max_inspo_images} inspiration images."},
        )

    total_size = 0
    upload_root = Path(settings.upload_dir) / str(tenant_id) / str(booking_id)
    upload_root.mkdir(parents=True, exist_ok=True)
    assets: list[BookingInspoAsset] = []

    for file in files:
        content_type = file.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={"error": "INVALID_INSPO_IMAGE", "message": "Style inspiration uploads must be image files."},
            )

        content = await file.read()
        size = len(content)
        total_size += size
        if size > settings.max_inspo_image_bytes or total_size > settings.max_inspo_total_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"error": "INSPO_IMAGE_TOO_LARGE", "message": "One or more inspiration images are too large."},
            )

        suffix = Path(file.filename or "image").suffix[:20]
        stored_filename = f"{uuid4()}{suffix}"
        path = upload_root / stored_filename
        path.write_bytes(content)
        url = f"{settings.upload_base_url.rstrip('/')}/{tenant_id}/{booking_id}/{stored_filename}"
        assets.append(
            BookingInspoAsset(
                booking_id=booking_id,
                tenant_id=tenant_id,
                original_filename=file.filename or "image",
                stored_filename=stored_filename,
                content_type=content_type,
                size_bytes=size,
                url=url,
            )
        )

    return assets
