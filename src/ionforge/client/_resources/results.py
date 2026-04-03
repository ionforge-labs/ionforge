"""Results resource (scoped to a job)."""

from __future__ import annotations

from collections.abc import Iterator

from .._generated import DownloadJobResultResponse, Result
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource


class JobResults(BaseSyncResource):
    """Results scoped to a specific job (sync)."""

    def __init__(self, transport: SyncTransport, job_id: str) -> None:
        super().__init__(transport)
        self._job_id = job_id

    def _base_path(self) -> str:
        return f"/jobs/{self._job_id}/results"

    def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Result]:
        """List result artifacts for this job."""
        data = self._get(
            self._base_path(),
            params={"limit": limit, "offset": offset},
        )
        return Page[Result].model_validate(data)

    def list_autopaginate(
        self,
        *,
        page_size: int = 25,
    ) -> Iterator[Result]:
        """Iterate over all results for this job."""
        return PageIterator(
            fetch=lambda offset: self.list(limit=page_size, offset=offset),
            page_size=page_size,
        )

    def download(self, id: str) -> DownloadJobResultResponse:
        """Get a pre-signed download URL for a result file."""
        data = self._get(f"{self._base_path()}/{id}/download")
        return DownloadJobResultResponse.model_validate(data)


class AsyncJobResults(BaseAsyncResource):
    """Results scoped to a specific job (async)."""

    def __init__(self, transport: AsyncTransport, job_id: str) -> None:
        super().__init__(transport)
        self._job_id = job_id

    def _base_path(self) -> str:
        return f"/jobs/{self._job_id}/results"

    async def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Result]:
        """List result artifacts for this job."""
        data = await self._get(
            self._base_path(),
            params={"limit": limit, "offset": offset},
        )
        return Page[Result].model_validate(data)

    def list_autopaginate(
        self,
        *,
        page_size: int = 25,
    ) -> AsyncPageIterator[Result]:
        """Iterate over all results for this job."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(limit=page_size, offset=offset),
            page_size=page_size,
        )

    async def download(self, id: str) -> DownloadJobResultResponse:
        """Get a pre-signed download URL for a result file."""
        data = await self._get(f"{self._base_path()}/{id}/download")
        return DownloadJobResultResponse.model_validate(data)
