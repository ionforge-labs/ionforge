"""Uploads resource."""

from __future__ import annotations

from .._generated import PresignUploadResponse
from ._base import BaseAsyncResource, BaseSyncResource


class Uploads(BaseSyncResource):
    """Synchronous uploads resource."""

    def presign(
        self,
        *,
        filename: str,
        content_type: str,
    ) -> PresignUploadResponse:
        """Get a pre-signed URL for uploading a file."""
        data = self._post(
            "/uploads/presign",
            body={"filename": filename, "contentType": content_type},
        )
        return PresignUploadResponse.model_validate(data)


class AsyncUploads(BaseAsyncResource):
    """Asynchronous uploads resource."""

    async def presign(
        self,
        *,
        filename: str,
        content_type: str,
    ) -> PresignUploadResponse:
        """Get a pre-signed URL for uploading a file."""
        data = await self._post(
            "/uploads/presign",
            body={"filename": filename, "contentType": content_type},
        )
        return PresignUploadResponse.model_validate(data)
