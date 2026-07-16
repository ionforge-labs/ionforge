"""Results resource (scoped to a run)."""

from __future__ import annotations

from collections.abc import Iterator

from ionforge._types._generated import (
    DownloadRunResultResponse,
    DownloadRunResultVizResponse,
    Result,
)

from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource


class RunResults(BaseSyncResource):
    """Results scoped to a specific run (sync)."""

    def __init__(self, transport: SyncTransport, run_id: str) -> None:
        super().__init__(transport)
        self._run_id = run_id

    def _base_path(self) -> str:
        return f"/runs/{self._run_id}/results"

    def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Result]:
        """List result artifacts for this run."""
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
        """Iterate over all results for this run."""
        return PageIterator(
            fetch=lambda offset: self.list(limit=page_size, offset=offset),
            page_size=page_size,
        )

    def download(self, id: str) -> DownloadRunResultResponse:
        """Get a pre-signed download URL for a result file."""
        data = self._get(f"{self._base_path()}/{id}/download")
        return DownloadRunResultResponse.model_validate(data)

    def viz(self, id: str) -> DownloadRunResultVizResponse:
        """Get the visualization payload for a result file."""
        data = self._get(f"{self._base_path()}/{id}/viz")
        return DownloadRunResultVizResponse.model_validate(data)


class AsyncRunResults(BaseAsyncResource):
    """Results scoped to a specific run (async)."""

    def __init__(self, transport: AsyncTransport, run_id: str) -> None:
        super().__init__(transport)
        self._run_id = run_id

    def _base_path(self) -> str:
        return f"/runs/{self._run_id}/results"

    async def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Result]:
        """List result artifacts for this run."""
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
        """Iterate over all results for this run."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(limit=page_size, offset=offset),
            page_size=page_size,
        )

    async def download(self, id: str) -> DownloadRunResultResponse:
        """Get a pre-signed download URL for a result file."""
        data = await self._get(f"{self._base_path()}/{id}/download")
        return DownloadRunResultResponse.model_validate(data)

    async def viz(self, id: str) -> DownloadRunResultVizResponse:
        """Get the visualization payload for a result file."""
        data = await self._get(f"{self._base_path()}/{id}/viz")
        return DownloadRunResultVizResponse.model_validate(data)
