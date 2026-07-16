"""Convenience-method tests: run_simulation, upload_geometry, download_results."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from ionforge.client import BeamParams, ModelParams, SolverParams
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
        poll_interval=0.0,
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
        poll_interval=0.0,
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


def _download_router() -> Router:
    return (
        Router()
        .json("GET", r"/v1/runs/run_1/results", page([make_result(id="res_1")]))
        .json("GET", r"/v1/runs/run_1/results/res_1/download", {"url": PRESIGNED_URL})
    )


def _presigned_handler(recorder: list[httpx.Request]):
    def handler(req: httpx.Request) -> httpx.Response:
        recorder.append(req)
        return httpx.Response(200, content=FILE_BYTES)

    return handler


def test_download_results_sync_writes_bytes_without_auth_leak(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from contextlib import contextmanager

    presigned_reqs: list[httpx.Request] = []
    mock = httpx.MockTransport(_presigned_handler(presigned_reqs))

    @contextmanager
    def fake_stream(method: str, url: str, **kwargs: object):
        with httpx.Client(transport=mock) as c, c.stream(method, url, **kwargs) as r:
            yield r

    monkeypatch.setattr(httpx, "stream", fake_stream)

    client = make_client(_download_router())
    paths = client.download_results("run_1", output_dir=tmp_path)

    assert len(paths) == 1
    assert paths[0].read_bytes() == FILE_BYTES
    # The presigned request went to the file host, carrying no Authorization.
    assert len(presigned_reqs) == 1
    assert presigned_reqs[0].url.host == "files.example.com"
    assert "authorization" not in {k.lower() for k in presigned_reqs[0].headers}


def test_download_results_async_writes_bytes_without_auth_leak(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    presigned_reqs: list[httpx.Request] = []
    mock = httpx.MockTransport(_presigned_handler(presigned_reqs))

    async def go() -> list[Path]:
        # Build the client first so its own transport is the API mock, then
        # patch AsyncClient so only the download uses the presigned mock.
        client = make_async_client(_download_router())
        real_async_client = httpx.AsyncClient
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda **kw: real_async_client(transport=mock, **kw),
        )
        paths = await client.download_results("run_1", output_dir=tmp_path)
        await client.close()
        return paths

    paths = asyncio.run(go())

    assert len(paths) == 1
    assert paths[0].read_bytes() == FILE_BYTES
    assert len(presigned_reqs) == 1
    assert presigned_reqs[0].url.host == "files.example.com"
    assert "authorization" not in {k.lower() for k in presigned_reqs[0].headers}
