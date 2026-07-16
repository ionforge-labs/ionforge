"""Models resource."""

from __future__ import annotations

import builtins
from collections.abc import Iterator
from typing import Any

from ionforge._types._generated import (
    CloneModelRequest,
    CreateModelRequest,
    ListModelTemplatesResponse,
    Model,
    ModelParams,
    ModelWithCounts,
    SimulatorType,
    UpdateModelRequest,
)

from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from ._base import BaseAsyncResource, BaseSyncResource
from ._coerce import to_enum, to_model
from .runs import AsyncModelRuns, ModelRuns
from .sweeps import AsyncModelSweeps, ModelSweeps


def _list_params(
    *,
    project_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    simulator_type: SimulatorType | str | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if project_id is not None:
        params["projectId"] = project_id
    if search is not None:
        params["search"] = search
    if simulator_type is not None:
        params["simulatorType"] = simulator_type
    return params


class Models(BaseSyncResource):
    """Synchronous models resource."""

    def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        simulator_type: SimulatorType | str | None = None,
        geometry_id: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
        is_template: bool | None = None,
    ) -> Model:
        """Create a model."""
        data = self._post(
            "/models",
            body=CreateModelRequest(
                project_id=project_id,
                name=name,
                description=description,
                simulator_type=to_enum(SimulatorType, simulator_type),
                geometry_id=geometry_id,
                params=to_model(ModelParams, params),
                is_template=is_template,
            ),
        )
        return Model.model_validate(data)

    def list(
        self,
        *,
        project_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
        simulator_type: SimulatorType | str | None = None,
    ) -> Page[Model]:
        """List models (paginated)."""
        data = self._get(
            "/models",
            params=_list_params(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
                simulator_type=simulator_type,
            ),
        )
        return Page[Model].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        search: str | None = None,
        simulator_type: SimulatorType | str | None = None,
        page_size: int = 25,
    ) -> Iterator[Model]:
        """Iterate over all models, fetching pages automatically."""
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

    def get(self, id: str) -> ModelWithCounts:
        """Get a model by ID."""
        data = self._get(f"/models/{id}")
        return ModelWithCounts.model_validate(data)

    def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        geometry_id: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
    ) -> Model:
        """Update a model."""
        data = self._put(
            f"/models/{id}",
            body=UpdateModelRequest(
                name=name,
                description=description,
                geometry_id=geometry_id,
                params=to_model(ModelParams, params),
            ),
        )
        return Model.model_validate(data)

    def delete(self, id: str) -> None:
        """Delete a model."""
        self._delete(f"/models/{id}")

    def list_templates(
        self,
        *,
        search: str | None = None,
        limit: int = 25,
    ) -> builtins.list[Model]:
        """List template models."""
        params: dict[str, object] = {"limit": limit}
        if search is not None:
            params["search"] = search
        data = self._get("/models/templates", params=params)
        return ListModelTemplatesResponse.model_validate(data).items

    def clone(
        self,
        *,
        template_id: str,
        project_id: str,
        name: str,
        description: str | None = None,
    ) -> Model:
        """Clone a template model into a project."""
        data = self._post(
            "/models/clone",
            body=CloneModelRequest(
                template_id=template_id,
                project_id=project_id,
                name=name,
                description=description,
            ),
        )
        return Model.model_validate(data)

    def runs(self, model_id: str) -> ModelRuns:
        """Access runs scoped to a specific model."""
        return ModelRuns(self._transport, model_id)

    def sweeps(self, model_id: str) -> ModelSweeps:
        """Access sweeps scoped to a specific model."""
        return ModelSweeps(self._transport, model_id)


class AsyncModels(BaseAsyncResource):
    """Asynchronous models resource."""

    async def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        simulator_type: SimulatorType | str | None = None,
        geometry_id: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
        is_template: bool | None = None,
    ) -> Model:
        """Create a model."""
        data = await self._post(
            "/models",
            body=CreateModelRequest(
                project_id=project_id,
                name=name,
                description=description,
                simulator_type=to_enum(SimulatorType, simulator_type),
                geometry_id=geometry_id,
                params=to_model(ModelParams, params),
                is_template=is_template,
            ),
        )
        return Model.model_validate(data)

    async def list(
        self,
        *,
        project_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
        simulator_type: SimulatorType | str | None = None,
    ) -> Page[Model]:
        """List models (paginated)."""
        data = await self._get(
            "/models",
            params=_list_params(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
                simulator_type=simulator_type,
            ),
        )
        return Page[Model].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        search: str | None = None,
        simulator_type: SimulatorType | str | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Model]:
        """Iterate over all models, fetching pages automatically."""
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

    async def get(self, id: str) -> ModelWithCounts:
        """Get a model by ID."""
        data = await self._get(f"/models/{id}")
        return ModelWithCounts.model_validate(data)

    async def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        geometry_id: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
    ) -> Model:
        """Update a model."""
        data = await self._put(
            f"/models/{id}",
            body=UpdateModelRequest(
                name=name,
                description=description,
                geometry_id=geometry_id,
                params=to_model(ModelParams, params),
            ),
        )
        return Model.model_validate(data)

    async def delete(self, id: str) -> None:
        """Delete a model."""
        await self._delete(f"/models/{id}")

    async def list_templates(
        self,
        *,
        search: str | None = None,
        limit: int = 25,
    ) -> builtins.list[Model]:
        """List template models."""
        params: dict[str, object] = {"limit": limit}
        if search is not None:
            params["search"] = search
        data = await self._get("/models/templates", params=params)
        return ListModelTemplatesResponse.model_validate(data).items

    async def clone(
        self,
        *,
        template_id: str,
        project_id: str,
        name: str,
        description: str | None = None,
    ) -> Model:
        """Clone a template model into a project."""
        data = await self._post(
            "/models/clone",
            body=CloneModelRequest(
                template_id=template_id,
                project_id=project_id,
                name=name,
                description=description,
            ),
        )
        return Model.model_validate(data)

    def runs(self, model_id: str) -> AsyncModelRuns:
        """Access runs scoped to a specific model."""
        return AsyncModelRuns(self._transport, model_id)

    def sweeps(self, model_id: str) -> AsyncModelSweeps:
        """Access sweeps scoped to a specific model."""
        return AsyncModelSweeps(self._transport, model_id)
