import hashlib
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import settings


class ImageStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredImage:
    provider: str
    key: str | None
    format: str | None
    data: bytes | None


def cloudinary_signature(parameters: dict[str, str | int | bool], api_secret: str) -> str:
    normalized = "&".join(
        f"{key}={str(value).lower() if isinstance(value, bool) else value}"
        for key, value in sorted(parameters.items())
        if value is not None and value != ""
    )
    return hashlib.sha1(f"{normalized}{api_secret}".encode()).hexdigest()


class DatabaseImageStorage:
    provider = "database"

    async def store(
        self,
        *,
        tenant_id: str,
        booking_id: str,
        object_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage:
        return StoredImage(provider=self.provider, key=None, format=None, data=content)

    async def delete(self, *, key: str | None) -> None:
        return None


class CloudinaryImageStorage:
    provider = "cloudinary"

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def store(
        self,
        *,
        tenant_id: str,
        booking_id: str,
        object_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage:
        timestamp = int(time.time())
        public_id = object_id
        parameters: dict[str, str | int | bool] = {
            "asset_folder": f"bookie/{tenant_id}/{booking_id}",
            "overwrite": False,
            "public_id": public_id,
            "timestamp": timestamp,
            "type": "authenticated",
        }
        data = {
            **{key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in parameters.items()},
            "api_key": self.api_key,
            "signature": cloudinary_signature(parameters, self.api_secret),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(
                    f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/upload",
                    data=data,
                    files={"file": (filename, content, content_type)},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ImageStorageError("Cloudinary image upload failed.") from exc

        returned_public_id = payload.get("public_id")
        returned_format = payload.get("format")
        if returned_public_id != public_id or payload.get("type") != "authenticated" or not returned_format:
            try:
                await self.delete(key=public_id)
            except ImageStorageError:
                pass
            raise ImageStorageError("Cloudinary returned an invalid upload response.")
        return StoredImage(provider=self.provider, key=returned_public_id, format=returned_format, data=None)

    async def delete(self, *, key: str | None) -> None:
        if not key:
            return
        timestamp = int(time.time())
        parameters: dict[str, str | int | bool] = {
            "invalidate": True,
            "public_id": key,
            "timestamp": timestamp,
            "type": "authenticated",
        }
        data = {
            **{name: str(value).lower() if isinstance(value, bool) else str(value) for name, value in parameters.items()},
            "api_key": self.api_key,
            "signature": cloudinary_signature(parameters, self.api_secret),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(
                    f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/destroy",
                    data=data,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ImageStorageError("Cloudinary image cleanup failed.") from exc

    def private_download_url(self, *, key: str, image_format: str, expires_at: int) -> str:
        timestamp = int(time.time())
        parameters: dict[str, str | int] = {
            "expires_at": expires_at,
            "format": image_format,
            "public_id": key,
            "timestamp": timestamp,
            "type": "authenticated",
        }
        query = {
            **parameters,
            "api_key": self.api_key,
            "signature": cloudinary_signature(parameters, self.api_secret),
        }
        return f"https://api.cloudinary.com/v1_1/{self.cloud_name}/image/download?{urlencode(query)}"


def get_image_storage():
    if settings.image_storage_provider == "cloudinary":
        return CloudinaryImageStorage(
            cloud_name=settings.cloudinary_cloud_name or "",
            api_key=settings.cloudinary_api_key or "",
            api_secret=settings.cloudinary_api_secret or "",
        )
    return DatabaseImageStorage()
