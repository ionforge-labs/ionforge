"""Sweeps resource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import TypeAdapter

from ionforge._types._generated import (
    Axes,
    Axes1,
    CreateModelSweepRequest,
    GetSweepAggregateResponse,
    ListSweepResultsResponse,
    ObjectiveDirection,
    ObjectiveMetric,
    Strategy,
    Sweep,
)

from .._dataframe import SweepResults
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource
from ._coerce import to_enum, to_list

# Public, readable aliases for the codegen axis models. A sweep axis varies
# either a model parameter (``ParamAxis``) or a geometry parameter
# (``GeometryAxis``) across a range of values.
ParamAxis = Axes
"""A sweep axis that varies a model parameter (``kind="param"``)."""
GeometryAxis = Axes1
"""A sweep axis that varies a geometry parameter (``kind="geometry"``)."""

# An axis is a ``ParamAxis``- or ``GeometryAxis``-valued dimension of the sweep.
SweepAxis = ParamAxis | GeometryAxis | dict[str, Any]

# Validates a list of axes (given as models or plain dicts) into the strict
# ``list[Axes | Axes1]`` the request model requires.
_AXES_ADAPTER: TypeAdapter[list[Axes | Axes1]] = TypeAdapter(list[Axes | Axes1])


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
        strategy: Strategy | str | None = None,
        random_count: int | None = None,
        objective_metric: ObjectiveMetric | str | None = None,
        objective_direction: ObjectiveDirection | str | None = None,
        parent_sweep_id: str | None = None,
    ) -> Sweep:
        """Create a parameter sweep for this model."""
        data = self._post(
            self._base_path(),
            body=CreateModelSweepRequest(
                name=name,
                axes=to_list(_AXES_ADAPTER, axes),
                strategy=to_enum(Strategy, strategy),
                random_count=random_count,
                objective_metric=to_enum(ObjectiveMetric, objective_metric),
                objective_direction=to_enum(ObjectiveDirection, objective_direction),
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
        strategy: Strategy | str | None = None,
        random_count: int | None = None,
        objective_metric: ObjectiveMetric | str | None = None,
        objective_direction: ObjectiveDirection | str | None = None,
        parent_sweep_id: str | None = None,
    ) -> Sweep:
        """Create a parameter sweep for this model."""
        data = await self._post(
            self._base_path(),
            body=CreateModelSweepRequest(
                name=name,
                axes=to_list(_AXES_ADAPTER, axes),
                strategy=to_enum(Strategy, strategy),
                random_count=random_count,
                objective_metric=to_enum(ObjectiveMetric, objective_metric),
                objective_direction=to_enum(ObjectiveDirection, objective_direction),
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

    def list_results(
        self,
        id: str,
        *,
        mode: str = "table",
        page_size: int = 100,
        max_rows: int | None = None,
    ) -> SweepResults:
        """Fetch all per-point results, auto-paginating across cursors.

        Assembles every page of :meth:`results` into a single
        :class:`~ionforge.client._dataframe.SweepResults` collection, ready for
        ``.to_dataframe()``. Set *max_rows* to cap the number of points pulled
        (guards against unbounded fetches for very large sweeps).
        """
        if max_rows is not None and max_rows <= 0:
            return SweepResults(rows=[], mode=mode, total_count=0)
        rows: list[Any] = []
        total_count = 0
        cursor: str | None = None
        while True:
            limit = page_size
            if max_rows is not None:
                limit = min(page_size, max_rows - len(rows))
            resp = self.results(id, mode=mode, limit=limit, cursor=cursor).root
            rows.extend(resp.rows)
            total_count = resp.total_count
            cursor = resp.next_cursor
            if cursor is None or (max_rows is not None and len(rows) >= max_rows):
                break
        if max_rows is not None:
            rows = rows[:max_rows]
        return SweepResults(rows=rows, mode=mode, total_count=total_count)

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

    async def list_results(
        self,
        id: str,
        *,
        mode: str = "table",
        page_size: int = 100,
        max_rows: int | None = None,
    ) -> SweepResults:
        """Fetch all per-point results, auto-paginating across cursors.

        Assembles every page of :meth:`results` into a single
        :class:`~ionforge.client._dataframe.SweepResults` collection, ready for
        ``.to_dataframe()``. Set *max_rows* to cap the number of points pulled
        (guards against unbounded fetches for very large sweeps).
        """
        if max_rows is not None and max_rows <= 0:
            return SweepResults(rows=[], mode=mode, total_count=0)
        rows: list[Any] = []
        total_count = 0
        cursor: str | None = None
        while True:
            limit = page_size
            if max_rows is not None:
                limit = min(page_size, max_rows - len(rows))
            resp = (await self.results(id, mode=mode, limit=limit, cursor=cursor)).root
            rows.extend(resp.rows)
            total_count = resp.total_count
            cursor = resp.next_cursor
            if cursor is None or (max_rows is not None and len(rows) >= max_rows):
                break
        if max_rows is not None:
            rows = rows[:max_rows]
        return SweepResults(rows=rows, mode=mode, total_count=total_count)

    async def aggregate(self, id: str) -> GetSweepAggregateResponse:
        """Get the aggregated objective surface and best point for a sweep."""
        data = await self._get(f"/sweeps/{id}/aggregate")
        return GetSweepAggregateResponse.model_validate(data)
