"""Resource tests: verb, path, and wire shape for each namespace."""

from __future__ import annotations

import json

import httpx
import pytest

from ionforge.client import BeamParams, ModelParams, SolverParams
from ionforge.client._resources.uploads import MAX_UPLOAD_SIZE_BYTES

from .conftest import (
    Router,
    make_client,
    make_geometry_meta,
    make_model,
    make_model_with_counts,
    make_project,
    make_project_with_counts,
    make_result,
    make_run,
    make_sweep,
    page,
)


def _body(req: httpx.Request) -> dict:
    return json.loads(req.content)


# --- projects --------------------------------------------------------------


def test_projects_create_posts_camelcase_body() -> None:
    router = Router().json("POST", r"/v1/projects", make_project(), status=201)
    client = make_client(router)
    client.projects.create(name="Lens study", description="desc")

    assert router.last.method == "POST"
    assert router.last.url.path == "/v1/projects"
    assert _body(router.last) == {"name": "Lens study", "description": "desc"}


def test_projects_create_excludes_none() -> None:
    router = Router().json("POST", r"/v1/projects", make_project())
    make_client(router).projects.create(name="Only name")
    assert _body(router.last) == {"name": "Only name"}


def test_projects_get_hits_id_path() -> None:
    router = Router().json("GET", r"/v1/projects/proj_9", make_project_with_counts())
    proj = make_client(router).projects.get("proj_9")
    assert router.last.url.path == "/v1/projects/proj_9"
    assert proj.id == "proj_1"


def test_projects_list_sends_pagination_params() -> None:
    router = Router().json("GET", r"/v1/projects", page([make_project()]))
    make_client(router).projects.list(limit=10, offset=5, search="ein")
    q = router.last.url.params
    assert q["limit"] == "10"
    assert q["offset"] == "5"
    assert q["search"] == "ein"


# --- geometries ------------------------------------------------------------


def test_geometries_create_wraps_geometry_data(einzel_serialized) -> None:
    router = Router().json("POST", r"/v1/geometries", make_geometry_meta())
    client = make_client(router)
    client.geometries.create(
        project_id="proj_1", name="lens", geometry_data=einzel_serialized
    )
    body = _body(router.last)
    assert body["projectId"] == "proj_1"
    assert body["name"] == "lens"
    assert body["geometryData"]["version"] == 1
    assert "description" not in body  # exclude_none


def test_geometries_list_filters_by_project() -> None:
    router = Router().json("GET", r"/v1/geometries", page([]))
    make_client(router).geometries.list(project_id="proj_7")
    assert router.last.url.params["projectId"] == "proj_7"


# --- models ----------------------------------------------------------------


def test_models_create_serializes_params_camelcase() -> None:
    router = Router().json("POST", r"/v1/models", make_model())
    client = make_client(router)
    params = ModelParams(
        solver=SolverParams(solver_type="bem_axisym"),
        beam=BeamParams(e_nominal=1000.0, n_particles=50),
    )
    client.models.create(
        project_id="proj_1", name="m", geometry_id="geo_1", params=params
    )
    body = _body(router.last)
    assert body["projectId"] == "proj_1"
    assert body["geometryId"] == "geo_1"
    assert body["params"]["solver"]["solver_type"] == "bem_axisym"
    assert body["params"]["beam"]["E_nominal"] == 1000.0
    assert body["params"]["beam"]["n_particles"] == 50


def test_models_get_returns_counts() -> None:
    router = Router().json("GET", r"/v1/models/mdl_1", make_model_with_counts())
    model = make_client(router).models.get("mdl_1")
    assert model.run_count == 0


def test_models_list_filters_simulator_type() -> None:
    router = Router().json("GET", r"/v1/models", page([make_model()]))
    make_client(router).models.list(simulator_type="ion_optics")
    assert router.last.url.params["simulatorType"] == "ion_optics"


# --- model-runs ------------------------------------------------------------


def test_model_runs_create_posts_to_nested_path() -> None:
    router = Router().json("POST", r"/v1/models/mdl_5/runs", make_run())
    client = make_client(router)
    client.models.runs("mdl_5").create(name="baseline", kind="simulate")
    assert router.last.url.path == "/v1/models/mdl_5/runs"
    body = _body(router.last)
    assert body == {"name": "baseline", "kind": "simulate"}


def test_model_runs_list_filters_status() -> None:
    router = Router().json("GET", r"/v1/models/mdl_5/runs", page([make_run()]))
    make_client(router).models.runs("mdl_5").list(status="running")
    assert router.last.url.params["status"] == "running"


# --- runs (top-level) ------------------------------------------------------


def test_runs_get_hits_id_path() -> None:
    router = Router().json("GET", r"/v1/runs/run_3", make_run(id="run_3"))
    run = make_client(router).runs.get("run_3")
    assert run.id == "run_3"


def test_runs_cancel_posts_to_cancel_path() -> None:
    router = Router().json(
        "POST", r"/v1/runs/run_3/cancel", make_run(status="cancelled")
    )
    run = make_client(router).runs.cancel("run_3")
    assert router.last.method == "POST"
    assert router.last.url.path == "/v1/runs/run_3/cancel"
    assert run.status == "cancelled"


def test_runs_list_filters_project() -> None:
    router = Router().json("GET", r"/v1/runs", page([make_run()]))
    make_client(router).runs.list(project_id="proj_2", status="completed")
    q = router.last.url.params
    assert q["projectId"] == "proj_2"
    assert q["status"] == "completed"


# --- sweeps ----------------------------------------------------------------


def test_model_sweeps_create_with_param_axis() -> None:
    router = Router().json("POST", r"/v1/models/mdl_1/sweeps", make_sweep())
    client = make_client(router)
    axis = {
        "kind": "param",
        "path": "beam.E_nominal",
        "range": {"type": "range", "min": 500.0, "max": 1500.0, "steps": 5},
    }
    client.models.sweeps("mdl_1").create(axes=[axis], strategy="grid")
    body = _body(router.last)
    assert router.last.url.path == "/v1/models/mdl_1/sweeps"
    assert body["axes"][0]["kind"] == "param"
    assert body["axes"][0]["path"] == "beam.E_nominal"
    assert body["axes"][0]["range"]["steps"] == 5
    assert body["strategy"] == "grid"


def test_model_sweeps_create_with_geometry_axis_values() -> None:
    router = Router().json("POST", r"/v1/models/mdl_1/sweeps", make_sweep())
    client = make_client(router)
    axis = {
        "kind": "geometry",
        "path": "tube_centre.voltage",
        "range": {"type": "values", "values": [-1000.0, -2000.0, -3000.0]},
    }
    client.models.sweeps("mdl_1").create(axes=[axis])
    body = _body(router.last)
    assert body["axes"][0]["kind"] == "geometry"
    assert body["axes"][0]["range"]["values"] == [-1000.0, -2000.0, -3000.0]


def test_sweeps_cancel_posts_to_cancel_path() -> None:
    router = Router().add(
        "POST", r"/v1/sweeps/swp_1/cancel", lambda _r: httpx.Response(204)
    )
    make_client(router).sweeps.cancel("swp_1")
    assert router.last.url.path == "/v1/sweeps/swp_1/cancel"


def test_sweeps_results_sends_mode_and_limit() -> None:
    router = Router().json(
        "GET",
        r"/v1/sweeps/swp_1/results",
        {"mode": "table", "rows": [], "nextCursor": None, "totalCount": 0},
    )
    make_client(router).sweeps.results("swp_1", mode="table", limit=50)
    q = router.last.url.params
    assert q["mode"] == "table"
    assert q["limit"] == "50"


# --- results ---------------------------------------------------------------


def test_run_results_list_hits_nested_path() -> None:
    router = Router().json("GET", r"/v1/runs/run_1/results", page([make_result()]))
    results = make_client(router).runs.results("run_1").list()
    assert router.last.url.path == "/v1/runs/run_1/results"
    assert results.items[0].id == "res_1"


def test_run_results_download_returns_url() -> None:
    router = Router().json(
        "GET",
        r"/v1/runs/run_1/results/res_1/download",
        {"url": "https://files.example.com/res_1?sig=abc"},
    )
    dl = make_client(router).runs.results("run_1").download("res_1")
    assert dl.url.startswith("https://files.example.com/")


# --- uploads ---------------------------------------------------------------


def test_uploads_presign_sends_size_bytes() -> None:
    router = Router().json(
        "POST", r"/v1/uploads/presign", {"url": "https://s3/x", "key": "k"}
    )
    client = make_client(router)
    resp = client.uploads.presign(
        filename="mesh.stl", content_type="model/stl", size_bytes=4096
    )
    body = _body(router.last)
    assert body["filename"] == "mesh.stl"
    assert body["contentType"] == "model/stl"
    assert body["sizeBytes"] == 4096
    assert resp.key == "k"


def test_uploads_presign_rejects_oversize_client_side() -> None:
    router = Router().json(
        "POST", r"/v1/uploads/presign", {"url": "https://s3/x", "key": "k"}
    )
    client = make_client(router)
    with pytest.raises(ValueError, match="exceeds the maximum"):
        client.uploads.presign(
            filename="big.stl",
            content_type="model/stl",
            size_bytes=MAX_UPLOAD_SIZE_BYTES + 1,
        )
    # No request should have been sent to the server.
    assert router.requests == []


def test_uploads_presign_rejects_nonpositive_size() -> None:
    router = Router().json(
        "POST", r"/v1/uploads/presign", {"url": "https://s3/x", "key": "k"}
    )
    with pytest.raises(ValueError, match="positive"):
        make_client(router).uploads.presign(
            filename="x", content_type="model/stl", size_bytes=0
        )
