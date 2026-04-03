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

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ionforge.geometry.builder import Geometry
    from ionforge.geometry.models import SerializedGeometry

from ionforge._types._generated import (
    BeamParams,
    Coils,
    Coils1,
    Coils2,
    DownloadJobResultResponse,
    EnsembleParams,
    GeometryListItem,
    GeometryMeta,
    GetGeometryResponse,
    IntegratorParams,
    Job,
    MagneticFieldParams,
    ParameterSpace,
    PresignUploadResponse,
    Project,
    ProjectWithCounts,
    Result,
    Simulation,
    SimulationParams,
    SimulationWithCounts,
    SolverParams,
    SpaceChargeParams,
    Sweep,
)

from ._config import resolve_config
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
from ._polling import async_poll_job, async_poll_sweep, poll_job, poll_sweep
from ._resources import (
    AsyncGeometries,
    AsyncJobs,
    AsyncProjects,
    AsyncSimulations,
    AsyncSweeps,
    AsyncUploads,
    Geometries,
    Jobs,
    Projects,
    Simulations,
    Sweeps,
    Uploads,
)
from ._transport import AsyncTransport, SyncTransport


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
    ) -> None:
        config = resolve_config(
            api_key=api_key,
            session_token=session_token,
            org_id=org_id,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._transport = SyncTransport(config)

        self.projects = Projects(self._transport)
        self.geometries = Geometries(self._transport)
        self.simulations = Simulations(self._transport)
        self.jobs = Jobs(self._transport)
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
        from ionforge.geometry.builder import Geometry as _Geometry

        sg = (
            geometry.to_serialized_geometry()
            if isinstance(geometry, _Geometry)
            else geometry
        )
        return self.geometries.create(
            project_id=project_id,
            name=name,
            description=description,
            geometry_data=sg,
        )

    def run_simulation(
        self,
        simulation_id: str,
        *,
        params: SimulationParams | dict[str, Any] | None = None,
        name: str | None = None,
        wait: bool = True,
        poll_interval: float = 2.0,
        poll_timeout: float = 600.0,
    ) -> Job:
        """Create a job and optionally wait for completion."""
        job = self.simulations.jobs(simulation_id).create(name=name, params=params)
        if wait:
            return poll_job(
                self.jobs,
                job.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return job

    def run_sweep(
        self,
        simulation_id: str,
        *,
        name: str,
        parameter_space: ParameterSpace,
        wait: bool = True,
        poll_interval: float = 5.0,
        poll_timeout: float = 3600.0,
    ) -> Sweep:
        """Create a parameter sweep and optionally wait for completion."""
        sweep = self.simulations.sweeps(simulation_id).create(
            name=name, parameter_space=parameter_space
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
        job_id: str,
        *,
        output_dir: str | Path = ".",
    ) -> list[Path]:
        """Download all result files for a completed job."""
        import httpx

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        downloaded: list[Path] = []
        for result in self.jobs.results(job_id).list_autopaginate():
            dl = self.jobs.results(job_id).download(result.id)
            filename = f"result-{result.id}"
            dest = output_path / filename
            with httpx.stream("GET", dl.url) as response:
                response.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            downloaded.append(dest)
        return downloaded

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
    ) -> None:
        config = resolve_config(
            api_key=api_key,
            session_token=session_token,
            org_id=org_id,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._transport = AsyncTransport(config)

        self.projects = AsyncProjects(self._transport)
        self.geometries = AsyncGeometries(self._transport)
        self.simulations = AsyncSimulations(self._transport)
        self.jobs = AsyncJobs(self._transport)
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
        from ionforge.geometry.builder import Geometry as _Geometry

        sg = (
            geometry.to_serialized_geometry()
            if isinstance(geometry, _Geometry)
            else geometry
        )
        return await self.geometries.create(
            project_id=project_id,
            name=name,
            description=description,
            geometry_data=sg,
        )

    async def run_simulation(
        self,
        simulation_id: str,
        *,
        params: SimulationParams | dict[str, Any] | None = None,
        name: str | None = None,
        wait: bool = True,
        poll_interval: float = 2.0,
        poll_timeout: float = 600.0,
    ) -> Job:
        """Create a job and optionally wait for completion."""
        job = await self.simulations.jobs(simulation_id).create(
            name=name, params=params
        )
        if wait:
            return await async_poll_job(
                self.jobs,
                job.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return job

    async def run_sweep(
        self,
        simulation_id: str,
        *,
        name: str,
        parameter_space: ParameterSpace,
        wait: bool = True,
        poll_interval: float = 5.0,
        poll_timeout: float = 3600.0,
    ) -> Sweep:
        """Create a parameter sweep and optionally wait for completion."""
        sweep = await self.simulations.sweeps(simulation_id).create(
            name=name, parameter_space=parameter_space
        )
        if wait:
            return await async_poll_sweep(
                self.sweeps,
                sweep.id,
                interval=poll_interval,
                timeout=poll_timeout,
            )
        return sweep

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
    "BeamParams",
    "Coils",
    "Coils1",
    "Coils2",
    "DownloadJobResultResponse",
    "EnsembleParams",
    "GeometryListItem",
    "GeometryMeta",
    "GetGeometryResponse",
    "IntegratorParams",
    "Job",
    "MagneticFieldParams",
    "Page",
    "ParameterSpace",
    "PresignUploadResponse",
    "Project",
    "ProjectWithCounts",
    "Result",
    "SimulationParams",
    "Simulation",
    "SimulationWithCounts",
    "SolverParams",
    "SpaceChargeParams",
    "Sweep",
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
    "poll_job",
    "async_poll_job",
    "poll_sweep",
    "async_poll_sweep",
]
