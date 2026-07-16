"""Uploads resource."""

from __future__ import annotations

from ionforge._types._generated import PresignUploadResponse

from ._base import BaseAsyncResource, BaseSyncResource

# Maximum size, in bytes, accepted for a presigned upload (100 MB).
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024


def _presign_body(
    filename: str, content_type: str, size_bytes: int
) -> dict[str, object]:
    if size_bytes <= 0:
        raise ValueError("size_bytes must be a positive number of bytes")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(
            f"size_bytes {size_bytes} exceeds the maximum of "
            f"{MAX_UPLOAD_SIZE_BYTES} bytes (100 MB)"
        )
    return {
        "filename": filename,
        "contentType": content_type,
        "sizeBytes": size_bytes,
    }


class Uploads(BaseSyncResource):
    """Synchronous uploads resource."""

    def presign(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> PresignUploadResponse:
        """Get a pre-signed URL for uploading a file (max 100 MB)."""
        data = self._post(
            "/uploads/presign",
            body=_presign_body(filename, content_type, size_bytes),
        )
        return PresignUploadResponse.model_validate(data)


class AsyncUploads(BaseAsyncResource):
    """Asynchronous uploads resource."""

    async def presign(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
    ) -> PresignUploadResponse:
        """Get a pre-signed URL for uploading a file (max 100 MB)."""
        data = await self._post(
            "/uploads/presign",
            body=_presign_body(filename, content_type, size_bytes),
        )
        return PresignUploadResponse.model_validate(data)
