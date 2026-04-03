"""Simulations resource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .._generated import (
    CloneSimulationRequest,
    CreateSimulationRequest,
    Simulation,
    SimulationParams,
    SimulationWithCounts,
    UpdateSimulationRequest,
)
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from ._base import BaseAsyncResource, BaseSyncResource
from .jobs import AsyncSimulationJobs, SimulationJobs
from .sweeps import AsyncSimulationSweeps, SimulationSweeps


def _list_params(
    *,
    project_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    simulator_type: str | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if project_id is not None:
        params["projectId"] = project_id
    if search is not None:
        params["search"] = search
    if simulator_type is not None:
        params["simulatorType"] = simulator_type
    return params


class Simulations(BaseSyncResource):
    """Synchronous simulations resource."""

    def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        simulator_type: str | None = None,
        geometry_id: str | None = None,
        params: SimulationParams | dict[str, Any] | None = None,
        is_template: bool | None = None,
    ) -> Simulation:
        """Create a simulation."""
        data = self._post(
            "/simulations",
            body=CreateSimulationRequest(
                project_id=project_id,
                name=name,
                description=description,
                simulator_type=simulator_type,
                geometry_id=geometry_id,
                params=params,
                is_template=is_template,
            ),
        )
        return Simulation.model_validate(data)

    def list(
        self,
        *,
        project_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
        simulator_type: str | None = None,
    ) -> Page[Simulation]:
        """List simulations (paginated)."""
        data = self._get(
            "/simulations",
            params=_list_params(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
                simulator_type=simulator_type,
            ),
        )
        return Page[Simulation].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        search: str | None = None,
        simulator_type: str | None = None,
        page_size: int = 25,
    ) -> Iterator[Simulation]:
        """Iterate over all simulations, fetching pages automatically."""
        return PageIterator(
            fetch=lambda offset: self.list(
                project_id=project_id,
                limit=page_size,
                offset=offset,
                search=search,
                simulator_type=simulator_type,
            ),
            page_size=page_size,
        )

    def get(self, id: str) -> SimulationWithCounts:
        """Get a simulation by ID."""
        data = self._get(f"/simulations/{id}")
        return SimulationWithCounts.model_validate(data)

    def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        geometry_id: str | None = None,
        params: SimulationParams | dict[str, Any] | None = None,
    ) -> Simulation:
        """Update a simulation."""
        data = self._put(
            f"/simulations/{id}",
            body=UpdateSimulationRequest(
                name=name,
                description=description,
                geometry_id=geometry_id,
                params=params,
            ),
        )
        return Simulation.model_validate(data)

    def delete(self, id: str) -> None:
        """Delete a simulation."""
        self._delete(f"/simulations/{id}")

    def list_templates(
        self,
        *,
        search: str | None = None,
        limit: int = 25,
    ) -> list[Simulation]:
        """List template simulations."""
        params: dict[str, object] = {"limit": limit}
        if search is not None:
            params["search"] = search
        data = self._get("/simulations/templates", params=params)
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Simulation.model_validate(item) for item in items]

    def clone(
        self,
        *,
        template_id: str,
        project_id: str,
        name: str,
        description: str | None = None,
    ) -> Simulation:
        """Clone a template simulation into a project."""
        data = self._post(
            "/simulations/clone",
            body=CloneSimulationRequest(
                template_id=template_id,
                project_id=project_id,
                name=name,
                description=description,
            ),
        )
        return Simulation.model_validate(data)

    def jobs(self, simulation_id: str) -> SimulationJobs:
        """Access jobs scoped to a specific simulation."""
        return SimulationJobs(self._transport, simulation_id)

    def sweeps(self, simulation_id: str) -> SimulationSweeps:
        """Access sweeps scoped to a specific simulation."""
        return SimulationSweeps(self._transport, simulation_id)


class AsyncSimulations(BaseAsyncResource):
    """Asynchronous simulations resource."""

    async def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        simulator_type: str | None = None,
        geometry_id: str | None = None,
        params: SimulationParams | dict[str, Any] | None = None,
        is_template: bool | None = None,
    ) -> Simulation:
        """Create a simulation."""
        data = await self._post(
            "/simulations",
            body=CreateSimulationRequest(
                project_id=project_id,
                name=name,
                description=description,
                simulator_type=simulator_type,
                geometry_id=geometry_id,
                params=params,
                is_template=is_template,
            ),
        )
        return Simulation.model_validate(data)

    async def list(
        self,
        *,
        project_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
        simulator_type: str | None = None,
    ) -> Page[Simulation]:
        """List simulations (paginated)."""
        data = await self._get(
            "/simulations",
            params=_list_params(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
                simulator_type=simulator_type,
            ),
        )
        return Page[Simulation].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        search: str | None = None,
        simulator_type: str | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Simulation]:
        """Iterate over all simulations, fetching pages automatically."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                project_id=project_id,
                limit=page_size,
                offset=offset,
                search=search,
                simulator_type=simulator_type,
            ),
            page_size=page_size,
        )

    async def get(self, id: str) -> SimulationWithCounts:
        """Get a simulation by ID."""
        data = await self._get(f"/simulations/{id}")
        return SimulationWithCounts.model_validate(data)

    async def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        geometry_id: str | None = None,
        params: SimulationParams | dict[str, Any] | None = None,
    ) -> Simulation:
        """Update a simulation."""
        data = await self._put(
            f"/simulations/{id}",
            body=UpdateSimulationRequest(
                name=name,
                description=description,
                geometry_id=geometry_id,
                params=params,
            ),
        )
        return Simulation.model_validate(data)

    async def delete(self, id: str) -> None:
        """Delete a simulation."""
        await self._delete(f"/simulations/{id}")

    async def list_templates(
        self,
        *,
        search: str | None = None,
        limit: int = 25,
    ) -> list[Simulation]:
        """List template simulations."""
        params: dict[str, object] = {"limit": limit}
        if search is not None:
            params["search"] = search
        data = await self._get("/simulations/templates", params=params)
        items = data.get("items", data) if isinstance(data, dict) else data
        return [Simulation.model_validate(item) for item in items]

    async def clone(
        self,
        *,
        template_id: str,
        project_id: str,
        name: str,
        description: str | None = None,
    ) -> Simulation:
        """Clone a template simulation into a project."""
        data = await self._post(
            "/simulations/clone",
            body=CloneSimulationRequest(
                template_id=template_id,
                project_id=project_id,
                name=name,
                description=description,
            ),
        )
        return Simulation.model_validate(data)

    def jobs(self, simulation_id: str) -> AsyncSimulationJobs:
        """Access jobs scoped to a specific simulation."""
        return AsyncSimulationJobs(self._transport, simulation_id)

    def sweeps(self, simulation_id: str) -> AsyncSimulationSweeps:
        """Access sweeps scoped to a specific simulation."""
        return AsyncSimulationSweeps(self._transport, simulation_id)
