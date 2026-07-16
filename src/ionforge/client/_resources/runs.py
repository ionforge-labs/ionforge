"""Runs resource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from ionforge._types._generated import (
    CreateModelRunRequest,
    Kind,
    ModelParams,
    Run,
    Status,
)

from .._dataframe import runs_to_dataframe
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from .._transport import AsyncTransport, SyncTransport
from ._base import BaseAsyncResource, BaseSyncResource
from ._coerce import to_enum, to_model

if TYPE_CHECKING:
    import pandas as pd

    from .results import AsyncRunResults, RunResults


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
# Model-scoped runs
# ---------------------------------------------------------------------------


class ModelRuns(BaseSyncResource):
    """Runs scoped to a specific model (sync)."""

    def __init__(self, transport: SyncTransport, model_id: str) -> None:
        super().__init__(transport)
        self._model_id = model_id

    def _base_path(self) -> str:
        return f"/models/{self._model_id}/runs"

    def create(
        self,
        *,
        name: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
        kind: Kind | str | None = None,
        parent_run_id: str | None = None,
    ) -> Run:
        """Launch a run for this model."""
        data = self._post(
            self._base_path(),
            body=CreateModelRunRequest(
                name=name,
                params=to_model(ModelParams, params),
                kind=to_enum(Kind, kind),
                parent_run_id=parent_run_id,
            ),
        )
        return Run.model_validate(data)

    def list(
        self,
        *,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Run]:
        """List runs for this model."""
        data = self._get(
            self._base_path(),
            params=_list_params(status=status, limit=limit, offset=offset),
        )
        return Page[Run].model_validate(data)

    def list_autopaginate(
        self,
        *,
        status: Status | None = None,
        page_size: int = 25,
    ) -> Iterator[Run]:
        """Iterate over all runs for this model."""
        return PageIterator(
            fetch=lambda offset: self.list(
                status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )


class AsyncModelRuns(BaseAsyncResource):
    """Runs scoped to a specific model (async)."""

    def __init__(self, transport: AsyncTransport, model_id: str) -> None:
        super().__init__(transport)
        self._model_id = model_id

    def _base_path(self) -> str:
        return f"/models/{self._model_id}/runs"

    async def create(
        self,
        *,
        name: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
        kind: Kind | str | None = None,
        parent_run_id: str | None = None,
    ) -> Run:
        """Launch a run for this model."""
        data = await self._post(
            self._base_path(),
            body=CreateModelRunRequest(
                name=name,
                params=to_model(ModelParams, params),
                kind=to_enum(Kind, kind),
                parent_run_id=parent_run_id,
            ),
        )
        return Run.model_validate(data)

    async def list(
        self,
        *,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Run]:
        """List runs for this model."""
        data = await self._get(
            self._base_path(),
            params=_list_params(status=status, limit=limit, offset=offset),
        )
        return Page[Run].model_validate(data)

    def list_autopaginate(
        self,
        *,
        status: Status | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Run]:
        """Iterate over all runs for this model."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )


# ---------------------------------------------------------------------------
# Top-level runs (cross-model)
# ---------------------------------------------------------------------------


class Runs(BaseSyncResource):
    """Top-level runs resource (cross-model, sync)."""

    def list(
        self,
        *,
        project_id: str | None = None,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Run]:
        """List all runs across models."""
        params = _list_params(status=status, limit=limit, offset=offset)
        if project_id is not None:
            params["projectId"] = project_id
        data = self._get("/runs", params=params)
        return Page[Run].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        status: Status | None = None,
        page_size: int = 25,
    ) -> Iterator[Run]:
        """Iterate over all runs."""
        return PageIterator(
            fetch=lambda offset: self.list(
                project_id=project_id, status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )

    def get(self, id: str) -> Run:
        """Get a run by ID."""
        data = self._get(f"/runs/{id}")
        return Run.model_validate(data)

    def cancel(self, id: str) -> Run:
        """Cancel a queued or running run."""
        data = self._post(f"/runs/{id}/cancel")
        return Run.model_validate(data)

    def results(self, run_id: str) -> RunResults:
        """Access results scoped to a specific run."""
        from .results import RunResults

        return RunResults(self._transport, run_id)

    def to_dataframe(
        self,
        *,
        project_id: str | None = None,
        status: Status | None = None,
        page_size: int = 25,
        max_rows: int | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame of runs (one row per run), auto-paginating.

        Projects the tabular fields of each run (id, name, status, simulator
        type, model/sweep ids, timestamps, error message). Set *max_rows* to
        cap the number of runs pulled. Requires the ``pandas`` extra.
        """
        runs = []
        for run in self.list_autopaginate(
            project_id=project_id, status=status, page_size=page_size
        ):
            runs.append(run)
            if max_rows is not None and len(runs) >= max_rows:
                break
        return runs_to_dataframe(runs)


class AsyncRuns(BaseAsyncResource):
    """Top-level runs resource (cross-model, async)."""

    async def list(
        self,
        *,
        project_id: str | None = None,
        status: Status | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Page[Run]:
        """List all runs across models."""
        params = _list_params(status=status, limit=limit, offset=offset)
        if project_id is not None:
            params["projectId"] = project_id
        data = await self._get("/runs", params=params)
        return Page[Run].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        status: Status | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Run]:
        """Iterate over all runs."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                project_id=project_id, status=status, limit=page_size, offset=offset
            ),
            page_size=page_size,
        )

    async def get(self, id: str) -> Run:
        """Get a run by ID."""
        data = await self._get(f"/runs/{id}")
        return Run.model_validate(data)

    async def cancel(self, id: str) -> Run:
        """Cancel a queued or running run."""
        data = await self._post(f"/runs/{id}/cancel")
        return Run.model_validate(data)

    def results(self, run_id: str) -> AsyncRunResults:
        """Access results scoped to a specific run."""
        from .results import AsyncRunResults

        return AsyncRunResults(self._transport, run_id)

    async def to_dataframe(
        self,
        *,
        project_id: str | None = None,
        status: Status | None = None,
        page_size: int = 25,
        max_rows: int | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame of runs (one row per run), auto-paginating.

        Projects the tabular fields of each run (id, name, status, simulator
        type, model/sweep ids, timestamps, error message). Set *max_rows* to
        cap the number of runs pulled. Requires the ``pandas`` extra.
        """
        runs = []
        async for run in self.list_autopaginate(
            project_id=project_id, status=status, page_size=page_size
        ):
            runs.append(run)
            if max_rows is not None and len(runs) >= max_rows:
                break
        return runs_to_dataframe(runs)
