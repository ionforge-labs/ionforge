"""Jobs resource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from .._generated import (
    CreateSimulationJobRequest,
    Job,
    SimulationParams,
    Status,
)
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource

if TYPE_CHECKING:
    from .results import AsyncJobResults, JobResults


def _list_params(
    *,
    status: Status | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if status is not None:
        params["status"] = status
    return params


# ---------------------------------------------------------------------------
# Simulation-scoped jobs
# ---------------------------------------------------------------------------


class SimulationJobs(BaseSyncResource):
    """Jobs scoped to a specific simulation (sync)."""

    def __init__(self, transport: SyncTransport, simulation_id: str) -> None:
        super().__init__(transport)
        self._simulation_id = simulation_id

    def _base_path(self) -> str:
        return f"/simulations/{self._simulation_id}/jobs"

    def create(
        self,
        *,
        name: str | None = None,
        params: SimulationParams | dict[str, Any] | None = None,
    ) -> Job:
        """Create a job for this simulation."""
        data = self._post(
            self._base_path(),
            body=CreateSimulationJobRequest(name=name, params=params),
        )
        return Job.model_validate(data)

    def list(
        self,
        *,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Job]:
        """List jobs for this simulation."""
        data = self._get(
            self._base_path(),
            params=_list_params(status=status, limit=limit, offset=offset),
        )
        return Page[Job].model_validate(data)

    def list_autopaginate(
        self,
        *,
        status: Status | None = None,
        page_size: int = 25,
    ) -> Iterator[Job]:
        """Iterate over all jobs for this simulation."""
        return PageIterator(
            fetch=lambda offset: self.list(
                status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )


class AsyncSimulationJobs(BaseAsyncResource):
    """Jobs scoped to a specific simulation (async)."""

    def __init__(self, transport: AsyncTransport, simulation_id: str) -> None:
        super().__init__(transport)
        self._simulation_id = simulation_id

    def _base_path(self) -> str:
        return f"/simulations/{self._simulation_id}/jobs"

    async def create(
        self,
        *,
        name: str | None = None,
        params: SimulationParams | dict[str, Any] | None = None,
    ) -> Job:
        """Create a job for this simulation."""
        data = await self._post(
            self._base_path(),
            body=CreateSimulationJobRequest(name=name, params=params),
        )
        return Job.model_validate(data)

    async def list(
        self,
        *,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Job]:
        """List jobs for this simulation."""
        data = await self._get(
            self._base_path(),
            params=_list_params(status=status, limit=limit, offset=offset),
        )
        return Page[Job].model_validate(data)

    def list_autopaginate(
        self,
        *,
        status: Status | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Job]:
        """Iterate over all jobs for this simulation."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )


# ---------------------------------------------------------------------------
# Top-level jobs (cross-simulation)
# ---------------------------------------------------------------------------


class Jobs(BaseSyncResource):
    """Top-level jobs resource (cross-simulation, sync)."""

    def list(
        self,
        *,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Job]:
        """List all jobs across simulations."""
        data = self._get(
            "/jobs",
            params=_list_params(status=status, limit=limit, offset=offset),
        )
        return Page[Job].model_validate(data)

    def list_autopaginate(
        self,
        *,
        status: Status | None = None,
        page_size: int = 25,
    ) -> Iterator[Job]:
        """Iterate over all jobs."""
        return PageIterator(
            fetch=lambda offset: self.list(
                status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )

    def get(self, id: str) -> Job:
        """Get a job by ID."""
        data = self._get(f"/jobs/{id}")
        return Job.model_validate(data)

    def cancel(self, id: str) -> Job:
        """Cancel a queued or running job."""
        data = self._post(f"/jobs/{id}/cancel")
        return Job.model_validate(data)

    def results(self, job_id: str) -> JobResults:
        """Access results scoped to a specific job."""
        from .results import JobResults

        return JobResults(self._transport, job_id)


class AsyncJobs(BaseAsyncResource):
    """Top-level jobs resource (cross-simulation, async)."""

    async def list(
        self,
        *,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Job]:
        """List all jobs across simulations."""
        data = await self._get(
            "/jobs",
            params=_list_params(status=status, limit=limit, offset=offset),
        )
        return Page[Job].model_validate(data)

    def list_autopaginate(
        self,
        *,
        status: Status | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Job]:
        """Iterate over all jobs."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )

    async def get(self, id: str) -> Job:
        """Get a job by ID."""
        data = await self._get(f"/jobs/{id}")
        return Job.model_validate(data)

    async def cancel(self, id: str) -> Job:
        """Cancel a queued or running job."""
        data = await self._post(f"/jobs/{id}/cancel")
        return Job.model_validate(data)

    def results(self, job_id: str) -> AsyncJobResults:
        """Access results scoped to a specific job."""
        from .results import AsyncJobResults

        return AsyncJobResults(self._transport, job_id)
