"""Convenience-method tests: run_simulation, upload_geometry, download_results."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from ionforge.client import BeamParams, ModelParams, NotFoundError, SolverParams
from ionforge.client import _polling as polling_mod

from .conftest import (
    Router,
    make_async_client,
    make_client,
    make_geometry_meta,
    make_model,
    make_result,
    make_run,
    page,
)

FILE_BYTES = b"trajectory-and-field-artifact-bytes"
PRESIGNED_URL = "https://files.example.com/results/res_1?sig=opaque"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(polling_mod.time, "sleep", lambda _s: None)


def _run_simulation_router() -> tuple[Router, dict]:
    """A router that models a full model->run->poll flow, capturing bodies."""
    captured: dict[str, dict] = {}
    poll = {"n": 0}

    def create_model(req: httpx.Request) -> httpx.Response:
        captured["model"] = json.loads(req.content)
        return httpx.Response(200, json=make_model(id="mdl_1"))

    def create_run(req: httpx.Request) -> httpx.Response:
        captured["run"] = json.loads(req.content)
        return httpx.Response(200, json=make_run(id="run_1", status="queued"))

    def get_run(_req: httpx.Request) -> httpx.Response:
        poll["n"] += 1
        status = "completed" if poll["n"] >= 2 else "running"
        return httpx.Response(200, json=make_run(id="run_1", status=status))

    router = (
        Router()
        .add("POST", r"/v1/models", create_model)
        .add("POST", r"/v1/models/mdl_1/runs", create_run)
        .add("GET", r"/v1/runs/run_1", get_run)
    )
    return router, captured


def test_run_simulation_full_flow_reaches_terminal() -> None:
    router, captured = _run_simulation_router()
    client = make_client(router)
    params = ModelParams(
        solver=SolverParams(solver_type="bem_axisym"),
        beam=BeamParams(e_nominal=1000.0, n_particles=100),
    )
    run = client.run_simulation(
        project_id="proj_1",
        name="einzel",
        geometry_id="geo_1",
        params=params,
        run_name="baseline",
        poll_interval=0.01,
        poll_timeout=10.0,
    )
    assert run.status == "completed"


def test_run_simulation_passes_params_to_model_not_run() -> None:
    router, captured = _run_simulation_router()
    client = make_client(router)
    client.run_simulation(
        project_id="proj_1",
        name="einzel",
        geometry_id="geo_1",
        params=ModelParams(beam=BeamParams(e_nominal=1000.0)),
        run_name="baseline",
        poll_interval=0.01,
    )
    # Params belong to the model; the run inherits them and must not resend them.
    assert "params" in captured["model"]
    assert captured["model"]["params"]["beam"]["E_nominal"] == 1000.0
    assert "params" not in captured["run"]
    assert captured["run"]["name"] == "baseline"


def test_run_simulation_no_wait_returns_immediately() -> None:
    router, _ = _run_simulation_router()
    client = make_client(router)
    run = client.run_simulation(
        project_id="proj_1", name="einzel", geometry_id="geo_1", wait=False
    )
    assert run.status == "queued"


def test_upload_geometry_accepts_builder(einzel_geometry) -> None:
    router = Router().json("POST", r"/v1/geometries", make_geometry_meta())
    client = make_client(router)
    client.upload_geometry("proj_1", "lens", einzel_geometry)
    body = json.loads(router.last.content)
    assert body["geometryData"]["version"] == 1
    assert body["geometryData"]["groups"][0]["name"] == "tube"


def test_upload_geometry_accepts_serialized(einzel_serialized) -> None:
    router = Router().json("POST", r"/v1/geometries", make_geometry_meta())
    client = make_client(router)
    client.upload_geometry("proj_1", "lens", einzel_serialized)
    body = json.loads(router.last.content)
    assert body["name"] == "lens"
    assert body["geometryData"]["version"] == 1


# --- download_results (presigned URL on a different host) ------------------
#
# The presigned URL lives on ``files.example.com`` (path ``/results/res_1``),
# a different host from the API. Both the API client and the transport's
# dedicated download client share the single injected ``MockTransport``, so the
# same router serves the API endpoints and the presigned file, letting each test
# assert the presigned request carried no ``Authorization`` header.


def _download_router(recorder: list[httpx.Request] | None = None) -> Router:
    def presigned(req: httpx.Request) -> httpx.Response:
        if recorder is not None:
            recorder.append(req)
        return httpx.Response(200, content=FILE_BYTES)

    return (
        Router()
        .json("GET", r"/v1/runs/run_1/results", page([make_result(id="res_1")]))
        .json("GET", r"/v1/runs/run_1/results/res_1/download", {"url": PRESIGNED_URL})
        .add("GET", r"/results/res_1", presigned)
    )


def test_download_results_sync_writes_bytes_without_auth_leak(tmp_path: Path) -> None:
    presigned_reqs: list[httpx.Request] = []
    client = make_client(_download_router(presigned_reqs))
    paths = client.download_results("run_1", output_dir=tmp_path)

    assert len(paths) == 1
    assert paths[0].read_bytes() == FILE_BYTES
    # The presigned request went to the file host, carrying no Authorization.
    assert len(presigned_reqs) == 1
    assert presigned_reqs[0].url.host == "files.example.com"
    assert "authorization" not in {k.lower() for k in presigned_reqs[0].headers}


def test_download_results_async_writes_bytes_without_auth_leak(tmp_path: Path) -> None:
    presigned_reqs: list[httpx.Request] = []

    async def go() -> list[Path]:
        client = make_async_client(_download_router(presigned_reqs))
        paths = await client.download_results("run_1", output_dir=tmp_path)
        await client.close()
        return paths

    paths = asyncio.run(go())

    assert len(paths) == 1
    assert paths[0].read_bytes() == FILE_BYTES
    assert len(presigned_reqs) == 1
    assert presigned_reqs[0].url.host == "files.example.com"
    assert "authorization" not in {k.lower() for k in presigned_reqs[0].headers}


def test_download_results_async_concurrent_writes_correct_files(tmp_path: Path) -> None:
    results = [make_result(id=f"res_{i}") for i in range(5)]

    def download(req: httpx.Request) -> httpx.Response:
        # /v1/runs/run_1/results/res_2/download -> res_2
        rid = req.url.path.split("/")[-2]
        return httpx.Response(
            200, json={"url": f"https://files.example.com/results/{rid}"}
        )

    def presigned(req: httpx.Request) -> httpx.Response:
        rid = req.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, content=f"body-{rid}".encode())

    router = (
        Router()
        .json("GET", r"/v1/runs/run_1/results", page(results))
        .add("GET", r"/v1/runs/run_1/results/res_\d+/download", download)
        .add("GET", r"/results/res_\d+", presigned)
    )

    async def go() -> list[Path]:
        client = make_async_client(router)
        paths = await client.download_results(
            "run_1", output_dir=tmp_path, concurrency=3
        )
        await client.close()
        return paths

    paths = asyncio.run(go())

    # One file per result, returned in result order, each with its own bytes.
    assert len(paths) == 5
    for i, path in enumerate(paths):
        assert path.name == f"result-res_{i}"
        assert path.read_bytes() == f"body-res_{i}".encode()


def test_download_results_async_cancels_siblings_on_first_failure(
    tmp_path: Path,
) -> None:
    """A single failed download cancels the outstanding ones and raises the
    original typed exception - no download outlives the call as an orphan.

    A plain ``asyncio.gather`` propagates the first child's exception but leaves
    its siblings running; here the streams are driven through a controlled fake
    so that one fails immediately while the rest are still in flight, and the
    test asserts every sibling received a ``CancelledError`` rather than being
    left to complete (or leak a warning) after the call returned.
    """
    results = [make_result(id=f"res_{i}") for i in range(5)]
    router = (
        Router()
        .json("GET", r"/v1/runs/run_1/results", page(results))
        .add(
            "GET",
            r"/v1/runs/run_1/results/res_\d+/download",
            lambda req: httpx.Response(
                200,
                json={
                    "url": f"https://files.example.com/results/{req.url.path.split('/')[-2]}"
                },
            ),
        )
    )

    started: list[str] = []
    cancelled: list[str] = []
    completed: list[str] = []

    async def fake_stream(url: str, dest: Path) -> None:
        started.append(url)
        if url.endswith("res_0"):
            # The first result's download fails terminally.
            raise NotFoundError("gone", status_code=404, body=None)
        try:
            # The siblings are still streaming when the failure surfaces.
            await asyncio.sleep(30)
            completed.append(url)
        except asyncio.CancelledError:
            cancelled.append(url)
            raise

    async def go() -> None:
        client = make_async_client(router)
        client._transport.stream_to_file = fake_stream  # type: ignore[method-assign]
        try:
            with pytest.raises(NotFoundError):
                await client.download_results("run_1", output_dir=tmp_path)
        finally:
            await client.close()

    asyncio.run(go())

    # The four siblings were all cancelled; none ran to completion as an orphan.
    assert sorted(cancelled) == [
        f"https://files.example.com/results/res_{i}" for i in range(1, 5)
    ]
    assert completed == []
    # No result files were left behind by the aborted download batch.
    assert list(tmp_path.iterdir()) == []
