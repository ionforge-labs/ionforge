"""IonForge Python API client.

Usage::

    from ionforge.client import IonForge

    client = IonForge(api_key="ifk_...")
    project = client.projects.create(name="My Project")

Install the optional dependency with::

    pip install ionforge[client]
"""

from __future__ import annotations

try:
    import httpx as _httpx  # noqa: F401
except ImportError as _exc:
    raise ImportError(
        "The ionforge API client requires httpx. "
        "Install it with: pip install ionforge[client]"
    ) from _exc

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ionforge.geometry.builder import Geometry
    from ionforge.geometry.models import SerializedGeometry

from ionforge._types._generated import (
    Axes,
    Axes1,
    BeamParams,
    Coils,
    Coils1,
    Coils2,
    DownloadRunResultResponse,
    DownloadRunResultVizResponse,
    EnsembleParams,
    GeometryListItem,
    GeometryMeta,
    GetGeometryResponse,
    GetSweepAggregateResponse,
    IntegratorParams,
    Kind,
    ListSweepResultsResponse,
    MagneticFieldParams,
    Model,
    ModelParams,
    ModelWithCounts,
    ObjectiveDirection,
    ObjectiveMetric,
    PresignUploadResponse,
    Project,
    ProjectWithCounts,
    Result,
    Run,
    SimulatorType,
    SolverParams,
    SpaceChargeParams,
    Status,
    Strategy,
    Sweep,
)

from ._config import resolve_config
from ._dataframe import SweepResults
from ._exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ConnectionError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from ._models.pagination import Page
from ._polling import async_poll_run, async_poll_sweep, poll_run, poll_sweep
from ._resources import (
    AsyncGeometries,
    AsyncModels,
    AsyncProjects,
    AsyncRuns,
    AsyncSweeps,
    AsyncUploads,
    Geometries,
    Models,
    Projects,
    Runs,
    Sweeps,
    Uploads,
)
from ._resources.sweeps import GeometryAxis, ParamAxis, SweepAxis
from ._transport import AsyncTransport, SyncTransport
from .results_io import (
    PSF,
    EnergyResolution,
    ResultSummary,
    RunResultData,
    Trajectory,
    load_result,
)


def _as_serialized_geometry(
    geometry: SerializedGeometry | Geometry,
) -> SerializedGeometry:
    """Coerce a geometry builder or serialised model into a ``SerializedGeometry``.

    Accepts either a :class:`~ionforge.geometry.builder.Geometry` builder (which
    is serialised) or an already-serialised model (passed through), so both
    ``upload_geometry`` variants share one coercion.
    """
    from ionforge.geometry.builder import Geometry as _Geometry

    if isinstance(geometry, _Geometry):
        return geometry.to_serialized_geometry()
    return geometry


class IonForge:
    """Synchronous IonForge API client.

    Usage::

        with IonForge(api_key="ifk_...") as client:
            projects = client.projects.list()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        session_token: str | None = None,
        org_id: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        _http_transport: _httpx.BaseTransport | None = None,
    ) -> None:
        config = resolve_config(
            api_key=api_key,
            session_token=session_token,
            org_id=org_id,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._transport = SyncTransport(config, http_transport=_http_transport)

        self.projects = Projects(self._transport)
        self.geometries = Geometries(self._transport)
        self.models = Models(self._transport)
        self.runs = Runs(self._transport)
        self.sweeps = Sweeps(self._transport)
        self.uploads = Uploads(self._transport)

    # -- Convenience methods ------------------------------------------------

    def upload_geometry(
        self,
        project_id: str,
        name: str,
        geometry: SerializedGeometry | Geometry,
        *,
        description: str | None = None,
    ) -> GeometryMeta:
        """Upload a geometry from a builder or serialised model."""
        return self.geometries.create(
            project_id=project_id,
            name=name,
            description=description,
            geometry_data=_as_serialized_geometry(geometry),
        )

    def run_simulation(
        self,
        *,
        project_id: str,
        name: str,
        geometry_id: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
        simulator_type: SimulatorType | str | None = None,
        run_name: str | None = None,
        kind: Kind | str | None = None,
        wait: bool = True,
        poll_interval: float = 2.0,
        poll_timeout: float = 600.0,
    ) -> Run:
        """Create a model, launch a run, and optionally wait for completion.

        Creates a model in *project_id*, launches a run against it, and (when
        *wait* is true) polls the run until it reaches a terminal state.

        The run inherits the model's *params*; to override parameters at the
        run level, use :meth:`ModelRuns.create` directly.
        """
        model = self.models.create(
            project_id=project_id,
            name=name,
            geometry_id=geometry_id,
            params=params,
            simulator_type=simulator_type,
        )
        run = self.models.runs(model.id).create(name=run_name, kind=kind)
        if wait:
            return poll_run(
                self.runs,
                run.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return run

    def run_sweep(
        self,
        model_id: str,
        *,
        axes: list[SweepAxis],
        name: str | None = None,
        strategy: Strategy | str | None = None,
        objective_metric: ObjectiveMetric | str | None = None,
        objective_direction: ObjectiveDirection | str | None = None,
        wait: bool = True,
        poll_interval: float = 5.0,
        poll_timeout: float = 3600.0,
    ) -> Sweep:
        """Create a parameter sweep for a model and optionally wait for completion."""
        sweep = self.models.sweeps(model_id).create(
            axes=axes,
            name=name,
            strategy=strategy,
            objective_metric=objective_metric,
            objective_direction=objective_direction,
        )
        if wait:
            return poll_sweep(
                self.sweeps,
                sweep.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return sweep

    def download_results(
        self,
        run_id: str,
        *,
        output_dir: str | Path = ".",
    ) -> list[Path]:
        """Download all result files for a completed run.

        Writes each result file to *output_dir* and returns their paths. Parse a
        downloaded file into numpy arrays and pandas frames with
        :func:`ionforge.client.load_result`, or use :meth:`load_results` to
        download and parse in one call.

        Each file streams through the transport's dedicated download client, so
        presigned URLs get the configured timeout, redirect following, retries,
        and the typed exception hierarchy, and never receive the API credential.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        downloaded: list[Path] = []
        for result in self.runs.results(run_id).list_autopaginate():
            dl = self.runs.results(run_id).download(result.id)
            dest = output_path / f"result-{result.id}"
            self._transport.stream_to_file(dl.url, dest)
            downloaded.append(dest)
        return downloaded

    def load_results(
        self,
        run_id: str,
        *,
        output_dir: str | Path = ".",
    ) -> list[RunResultData]:
        """Download a run's result files and parse each into a ``RunResultData``.

        Convenience wrapper over :meth:`download_results` followed by
        :func:`ionforge.client.load_result` on every downloaded file.
        """
        paths = self.download_results(run_id, output_dir=output_dir)
        return [load_result(path) for path in paths]

    # -- Context manager ----------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._transport.close()

    def __enter__(self) -> IonForge:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsyncIonForge:
    """Asynchronous IonForge API client.

    Usage::

        async with AsyncIonForge(api_key="ifk_...") as client:
            projects = await client.projects.list()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        session_token: str | None = None,
        org_id: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        _http_transport: _httpx.AsyncBaseTransport | None = None,
    ) -> None:
        config = resolve_config(
            api_key=api_key,
            session_token=session_token,
            org_id=org_id,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._transport = AsyncTransport(config, http_transport=_http_transport)

        self.projects = AsyncProjects(self._transport)
        self.geometries = AsyncGeometries(self._transport)
        self.models = AsyncModels(self._transport)
        self.runs = AsyncRuns(self._transport)
        self.sweeps = AsyncSweeps(self._transport)
        self.uploads = AsyncUploads(self._transport)

    # -- Convenience methods ------------------------------------------------

    async def upload_geometry(
        self,
        project_id: str,
        name: str,
        geometry: SerializedGeometry | Geometry,
        *,
        description: str | None = None,
    ) -> GeometryMeta:
        """Upload a geometry from a builder or serialised model."""
        return await self.geometries.create(
            project_id=project_id,
            name=name,
            description=description,
            geometry_data=_as_serialized_geometry(geometry),
        )

    async def run_simulation(
        self,
        *,
        project_id: str,
        name: str,
        geometry_id: str | None = None,
        params: ModelParams | dict[str, Any] | None = None,
        simulator_type: SimulatorType | str | None = None,
        run_name: str | None = None,
        kind: Kind | str | None = None,
        wait: bool = True,
        poll_interval: float = 2.0,
        poll_timeout: float = 600.0,
    ) -> Run:
        """Create a model, launch a run, and optionally wait for completion.

        Creates a model in *project_id*, launches a run against it, and (when
        *wait* is true) polls the run until it reaches a terminal state.

        The run inherits the model's *params*; to override parameters at the
        run level, use :meth:`AsyncModelRuns.create` directly.
        """
        model = await self.models.create(
            project_id=project_id,
            name=name,
            geometry_id=geometry_id,
            params=params,
            simulator_type=simulator_type,
        )
        run = await self.models.runs(model.id).create(name=run_name, kind=kind)
        if wait:
            return await async_poll_run(
                self.runs,
                run.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return run

    async def run_sweep(
        self,
        model_id: str,
        *,
        axes: list[SweepAxis],
        name: str | None = None,
        strategy: Strategy | str | None = None,
        objective_metric: ObjectiveMetric | str | None = None,
        objective_direction: ObjectiveDirection | str | None = None,
        wait: bool = True,
        poll_interval: float = 5.0,
        poll_timeout: float = 3600.0,
    ) -> Sweep:
        """Create a parameter sweep for a model and optionally wait for completion."""
        sweep = await self.models.sweeps(model_id).create(
            axes=axes,
            name=name,
            strategy=strategy,
            objective_metric=objective_metric,
            objective_direction=objective_direction,
        )
        if wait:
            return await async_poll_sweep(
                self.sweeps,
                sweep.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return sweep

    async def download_results(
        self,
        run_id: str,
        *,
        output_dir: str | Path = ".",
        concurrency: int = 8,
    ) -> list[Path]:
        """Download all result files for a completed run.

        Writes each result file to *output_dir* and returns their paths, in the
        run's result order. Parse a downloaded file into numpy arrays and pandas
        frames with :func:`ionforge.client.load_result`, or use
        :meth:`load_results` to download and parse in one call.

        Files stream concurrently (at most *concurrency* at once) through the
        transport's dedicated download client, so presigned URLs get the
        configured timeout, redirect following, retries, and the typed exception
        hierarchy, and never receive the API credential.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        jobs: list[tuple[Path, str]] = []
        async for result in self.runs.results(run_id).list_autopaginate():
            dl = await self.runs.results(run_id).download(result.id)
            jobs.append((output_path / f"result-{result.id}", dl.url))

        semaphore = asyncio.Semaphore(concurrency)

        async def _stream(dest: Path, url: str) -> Path:
            async with semaphore:
                await self._transport.stream_to_file(url, dest)
            return dest

        return list(await asyncio.gather(*(_stream(dest, url) for dest, url in jobs)))

    async def load_results(
        self,
        run_id: str,
        *,
        output_dir: str | Path = ".",
    ) -> list[RunResultData]:
        """Download a run's result files and parse each into a ``RunResultData``.

        Convenience wrapper over :meth:`download_results` followed by
        :func:`ionforge.client.load_result` on every downloaded file.
        """
        paths = await self.download_results(run_id, output_dir=output_dir)
        return [load_result(path) for path in paths]

    # -- Context manager ----------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._transport.close()

    async def __aenter__(self) -> AsyncIonForge:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


__all__ = [
    # Client classes
    "IonForge",
    "AsyncIonForge",
    # Generated models
    "Axes",
    "Axes1",
    "BeamParams",
    "Coils",
    "Coils1",
    "Coils2",
    "DownloadRunResultResponse",
    "DownloadRunResultVizResponse",
    "EnsembleParams",
    "GeometryListItem",
    "GeometryMeta",
    "GetGeometryResponse",
    "GetSweepAggregateResponse",
    "IntegratorParams",
    "ListSweepResultsResponse",
    "MagneticFieldParams",
    "Model",
    "ModelParams",
    "ModelWithCounts",
    "Page",
    "PresignUploadResponse",
    "Project",
    "ProjectWithCounts",
    "Result",
    "Run",
    "SolverParams",
    "SpaceChargeParams",
    "Status",
    "Sweep",
    "SweepAxis",
    "SweepResults",
    "ParamAxis",
    "GeometryAxis",
    # Result-file loaders
    "load_result",
    "RunResultData",
    "ResultSummary",
    "EnergyResolution",
    "PSF",
    "Trajectory",
    # Exceptions
    "APIError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "ConnectionError",
    "InternalServerError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    # Polling
    "poll_run",
    "async_poll_run",
    "poll_sweep",
    "async_poll_sweep",
]
