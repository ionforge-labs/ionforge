"""Sweeps resource."""

from __future__ import annotations

from collections.abc import Iterator

from .._generated import (
    CreateSimulationSweepRequest,
    ParameterSpace,
    Sweep,
)
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource

# ---------------------------------------------------------------------------
# Simulation-scoped sweeps
# ---------------------------------------------------------------------------


class SimulationSweeps(BaseSyncResource):
    """Sweeps scoped to a specific simulation (sync)."""

    def __init__(self, transport: SyncTransport, simulation_id: str) -> None:
        super().__init__(transport)
        self._simulation_id = simulation_id

    def _base_path(self) -> str:
        return f"/simulations/{self._simulation_id}/sweeps"

    def create(
        self,
        *,
        name: str,
        parameter_space: ParameterSpace,
    ) -> Sweep:
        """Create a parameter sweep for this simulation."""
        data = self._post(
            self._base_path(),
            body=CreateSimulationSweepRequest(
                name=name, parameter_space=parameter_space
            ),
        )
        return Sweep.model_validate(data)

    def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Sweep]:
        """List sweeps for this simulation."""
        data = self._get(
            self._base_path(),
            params={"limit": limit, "offset": offset},
        )
        return Page[Sweep].model_validate(data)

    def list_autopaginate(
        self,
        *,
        page_size: int = 25,
    ) -> Iterator[Sweep]:
        """Iterate over all sweeps for this simulation."""
        return PageIterator(
            fetch=lambda offset: self.list(limit=page_size, offset=offset),
            page_size=page_size,
        )


class AsyncSimulationSweeps(BaseAsyncResource):
    """Sweeps scoped to a specific simulation (async)."""

    def __init__(self, transport: AsyncTransport, simulation_id: str) -> None:
        super().__init__(transport)
        self._simulation_id = simulation_id

    def _base_path(self) -> str:
        return f"/simulations/{self._simulation_id}/sweeps"

    async def create(
        self,
        *,
        name: str,
        parameter_space: ParameterSpace,
    ) -> Sweep:
        """Create a parameter sweep for this simulation."""
        data = await self._post(
            self._base_path(),
            body=CreateSimulationSweepRequest(
                name=name, parameter_space=parameter_space
            ),
        )
        return Sweep.model_validate(data)

    async def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Sweep]:
        """List sweeps for this simulation."""
        data = await self._get(
            self._base_path(),
            params={"limit": limit, "offset": offset},
        )
        return Page[Sweep].model_validate(data)

    def list_autopaginate(
        self,
        *,
        page_size: int = 25,
    ) -> AsyncPageIterator[Sweep]:
        """Iterate over all sweeps for this simulation."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(limit=page_size, offset=offset),
            page_size=page_size,
        )


# ---------------------------------------------------------------------------
# Top-level sweeps (get / cancel by ID)
# ---------------------------------------------------------------------------


class Sweeps(BaseSyncResource):
    """Top-level sweeps resource (sync)."""

    def get(self, id: str) -> Sweep:
        """Get a sweep by ID."""
        data = self._get(f"/sweeps/{id}")
        return Sweep.model_validate(data)

    def cancel(self, id: str) -> None:
        """Cancel all queued jobs in a sweep."""
        self._post(f"/sweeps/{id}/cancel")


class AsyncSweeps(BaseAsyncResource):
    """Top-level sweeps resource (async)."""

    async def get(self, id: str) -> Sweep:
        """Get a sweep by ID."""
        data = await self._get(f"/sweeps/{id}")
        return Sweep.model_validate(data)

    async def cancel(self, id: str) -> None:
        """Cancel all queued jobs in a sweep."""
        await self._post(f"/sweeps/{id}/cancel")
