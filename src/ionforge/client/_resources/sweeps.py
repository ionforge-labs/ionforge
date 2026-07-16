"""Sweeps resource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ionforge._types._generated import (
    Axes,
    Axes1,
    CreateModelSweepRequest,
    GetSweepAggregateResponse,
    ListSweepResultsResponse,
    Sweep,
)

from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource

# An axis is a param- or geometry-valued dimension of the sweep.
SweepAxis = Axes | Axes1 | dict[str, Any]


# ---------------------------------------------------------------------------
# Model-scoped sweeps
# ---------------------------------------------------------------------------


class ModelSweeps(BaseSyncResource):
    """Sweeps scoped to a specific model (sync)."""

    def __init__(self, transport: SyncTransport, model_id: str) -> None:
        super().__init__(transport)
        self._model_id = model_id

    def _base_path(self) -> str:
        return f"/models/{self._model_id}/sweeps"

    def create(
        self,
        *,
        axes: list[SweepAxis],
        name: str | None = None,
        strategy: str | None = None,
        random_count: int | None = None,
        objective_metric: str | None = None,
        objective_direction: str | None = None,
        parent_sweep_id: str | None = None,
    ) -> Sweep:
        """Create a parameter sweep for this model."""
        data = self._post(
            self._base_path(),
            body=CreateModelSweepRequest(
                name=name,
                axes=axes,
                strategy=strategy,
                random_count=random_count,
                objective_metric=objective_metric,
                objective_direction=objective_direction,
                parent_sweep_id=parent_sweep_id,
            ),
        )
        return Sweep.model_validate(data)


class AsyncModelSweeps(BaseAsyncResource):
    """Sweeps scoped to a specific model (async)."""

    def __init__(self, transport: AsyncTransport, model_id: str) -> None:
        super().__init__(transport)
        self._model_id = model_id

    def _base_path(self) -> str:
        return f"/models/{self._model_id}/sweeps"

    async def create(
        self,
        *,
        axes: list[SweepAxis],
        name: str | None = None,
        strategy: str | None = None,
        random_count: int | None = None,
        objective_metric: str | None = None,
        objective_direction: str | None = None,
        parent_sweep_id: str | None = None,
    ) -> Sweep:
        """Create a parameter sweep for this model."""
        data = await self._post(
            self._base_path(),
            body=CreateModelSweepRequest(
                name=name,
                axes=axes,
                strategy=strategy,
                random_count=random_count,
                objective_metric=objective_metric,
                objective_direction=objective_direction,
                parent_sweep_id=parent_sweep_id,
            ),
        )
        return Sweep.model_validate(data)


# ---------------------------------------------------------------------------
# Top-level sweeps (list / get / cancel / results / aggregate)
# ---------------------------------------------------------------------------


def _list_params(
    *,
    model_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if model_id is not None:
        params["modelId"] = model_id
    return params


class Sweeps(BaseSyncResource):
    """Top-level sweeps resource (sync)."""

    def list(
        self,
        *,
        model_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Sweep]:
        """List sweeps (paginated)."""
        data = self._get(
            "/sweeps",
            params=_list_params(model_id=model_id, limit=limit, offset=offset),
        )
        return Page[Sweep].model_validate(data)

    def list_autopaginate(
        self,
        *,
        model_id: str | None = None,
        page_size: int = 25,
    ) -> Iterator[Sweep]:
        """Iterate over all sweeps, fetching pages automatically."""
        return PageIterator(
            fetch=lambda offset: self.list(
                model_id=model_id, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )

    def get(self, id: str) -> Sweep:
        """Get a sweep by ID."""
        data = self._get(f"/sweeps/{id}")
        return Sweep.model_validate(data)

    def cancel(self, id: str) -> None:
        """Cancel all queued runs in a sweep."""
        self._post(f"/sweeps/{id}/cancel")

    def results(
        self,
        id: str,
        *,
        mode: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ListSweepResultsResponse:
        """List per-point results for a sweep."""
        params: dict[str, object] = {"limit": limit}
        if mode is not None:
            params["mode"] = mode
        if cursor is not None:
            params["cursor"] = cursor
        data = self._get(f"/sweeps/{id}/results", params=params)
        return ListSweepResultsResponse.model_validate(data)

    def aggregate(self, id: str) -> GetSweepAggregateResponse:
        """Get the aggregated objective surface and best point for a sweep."""
        data = self._get(f"/sweeps/{id}/aggregate")
        return GetSweepAggregateResponse.model_validate(data)


class AsyncSweeps(BaseAsyncResource):
    """Top-level sweeps resource (async)."""

    async def list(
        self,
        *,
        model_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Sweep]:
        """List sweeps (paginated)."""
        data = await self._get(
            "/sweeps",
            params=_list_params(model_id=model_id, limit=limit, offset=offset),
        )
        return Page[Sweep].model_validate(data)

    def list_autopaginate(
        self,
        *,
        model_id: str | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Sweep]:
        """Iterate over all sweeps, fetching pages automatically."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                model_id=model_id, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )

    async def get(self, id: str) -> Sweep:
        """Get a sweep by ID."""
        data = await self._get(f"/sweeps/{id}")
        return Sweep.model_validate(data)

    async def cancel(self, id: str) -> None:
        """Cancel all queued runs in a sweep."""
        await self._post(f"/sweeps/{id}/cancel")

    async def results(
        self,
        id: str,
        *,
        mode: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ListSweepResultsResponse:
        """List per-point results for a sweep."""
        params: dict[str, object] = {"limit": limit}
        if mode is not None:
            params["mode"] = mode
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._get(f"/sweeps/{id}/results", params=params)
        return ListSweepResultsResponse.model_validate(data)

    async def aggregate(self, id: str) -> GetSweepAggregateResponse:
        """Get the aggregated objective surface and best point for a sweep."""
        data = await self._get(f"/sweeps/{id}/aggregate")
        return GetSweepAggregateResponse.model_validate(data)
