"""Tests for the pandas DataFrame accessors on sweep and run results.

Every test drives the real client stack against an ``httpx.MockTransport``
router, then exercises ``to_dataframe`` over the assembled result collections.
"""

from __future__ import annotations

import asyncio
import builtins
import sys

import httpx
import pandas as pd
import pytest

from ionforge.client._dataframe import _flatten

from .conftest import (
    Router,
    make_async_client,
    make_client,
    make_run,
    make_sweep_row,
    page,
    sweep_results_page,
)

# --- sweep results ---------------------------------------------------------


def test_sweep_to_dataframe_columns_and_dtypes() -> None:
    rows = [
        make_sweep_row(runId="run_1", sweepPoint={"beam.E_nominal": 1000.0}),
        make_sweep_row(runId="run_2", sweepPoint={"beam.E_nominal": 2000.0}),
    ]
    router = Router().json("GET", r"/v1/sweeps/swp_1/results", sweep_results_page(rows))
    df = make_client(router).sweeps.list_results("swp_1").to_dataframe()

    assert list(df.columns) == [
        "run_id",
        "status",
        "objective",
        "completed_at",
        "duration_seconds",
        "error",
        "param.beam.E_nominal",
    ]
    assert len(df) == 2
    # A swept numeric parameter comes through as a numeric column.
    assert pd.api.types.is_numeric_dtype(df["param.beam.E_nominal"])
    assert pd.api.types.is_numeric_dtype(df["objective"])
    assert pd.api.types.is_numeric_dtype(df["duration_seconds"])
    # Timestamps are parsed into a datetime dtype.
    assert pd.api.types.is_datetime64_any_dtype(df["completed_at"])
    assert df["param.beam.E_nominal"].tolist() == [1000.0, 2000.0]


def test_sweep_to_dataframe_flattens_multiple_axes() -> None:
    rows = [
        make_sweep_row(
            sweepPoint={"beam.E_nominal": 1000.0, "tube.voltage": -500.0},
        ),
    ]
    router = Router().json("GET", r"/v1/sweeps/swp_1/results", sweep_results_page(rows))
    df = make_client(router).sweeps.list_results("swp_1").to_dataframe()
    # Both dot-path axes become their own ``param.`` columns, sorted after base.
    assert list(df.columns)[-2:] == ["param.beam.E_nominal", "param.tube.voltage"]
    assert df["param.tube.voltage"].tolist() == [-500.0]


def test_flatten_raises_on_duplicate_dot_path() -> None:
    # A flat dot-path and a nested mapping that collapse to the same column are
    # a malformed payload; flattening must fail loud rather than last-wins.
    with pytest.raises(ValueError, match=r"duplicate dot-path column 'beam\.E'"):
        _flatten({"beam.E": 1.0, "beam": {"E": 2.0}})


def test_sweep_param_prefix_is_collision_proof_with_base_columns() -> None:
    # A swept param whose dot-path matches a base column lands under ``param.``
    # and so cannot overwrite the base ``status`` column.
    rows = [
        make_sweep_row(runId="run_1", sweepPoint={"status": 42.0}),
    ]
    router = Router().json("GET", r"/v1/sweeps/swp_1/results", sweep_results_page(rows))
    df = make_client(router).sweeps.list_results("swp_1").to_dataframe()
    assert "param.status" in df.columns
    assert df["param.status"].tolist() == [42.0]
    # The base status column is untouched (its default sweep-row value).
    assert "status" in df.columns
    assert df["param.status"].tolist() != df["status"].tolist()


def test_sweep_to_dataframe_full_mode_summary_columns() -> None:
    rows = [
        make_sweep_row(
            resultSummary={"transmission": 0.9, "mean_exit_energy_ev": 998.2},
        ),
    ]
    router = Router().json(
        "GET",
        r"/v1/sweeps/swp_1/results",
        sweep_results_page(rows, mode="full"),
    )
    results = make_client(router).sweeps.list_results("swp_1", mode="full")
    df = results.to_dataframe()
    assert results.mode == "full"
    assert "summary.transmission" in df.columns
    assert "summary.mean_exit_energy_ev" in df.columns
    assert df["summary.transmission"].tolist() == [0.9]


def test_sweep_list_results_assembles_multiple_pages() -> None:
    page_one = sweep_results_page(
        [make_sweep_row(runId="run_1")],
        next_cursor="cursor_2",
        total_count=2,
    )
    page_two = sweep_results_page(
        [make_sweep_row(runId="run_2")],
        next_cursor=None,
        total_count=2,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("cursor")
        return httpx.Response(200, json=page_two if cursor else page_one)

    router = Router().add("GET", r"/v1/sweeps/swp_1/results", handler)
    results = make_client(router).sweeps.list_results("swp_1", page_size=1)

    assert len(results) == 2
    assert results.total_count == 2
    df = results.to_dataframe()
    assert df["run_id"].tolist() == ["run_1", "run_2"]
    # Two pages fetched: first without a cursor, second with it.
    cursors = [r.url.params.get("cursor") for r in router.requests]
    assert cursors == [None, "cursor_2"]


def test_sweep_list_results_respects_max_rows() -> None:
    page_one = sweep_results_page(
        [make_sweep_row(runId="run_1"), make_sweep_row(runId="run_2")],
        next_cursor="cursor_2",
        total_count=10,
    )
    router = Router().json("GET", r"/v1/sweeps/swp_1/results", page_one)
    results = make_client(router).sweeps.list_results("swp_1", page_size=2, max_rows=2)
    # Cap reached after the first page; no second request is made.
    assert len(results) == 2
    assert len(router.requests) == 1


def test_sweep_to_dataframe_empty_has_base_columns() -> None:
    router = Router().json("GET", r"/v1/sweeps/swp_1/results", sweep_results_page([]))
    df = make_client(router).sweeps.list_results("swp_1").to_dataframe()
    assert len(df) == 0
    assert list(df.columns) == [
        "run_id",
        "status",
        "objective",
        "completed_at",
        "duration_seconds",
        "error",
    ]


# --- run listings ----------------------------------------------------------


def test_runs_to_dataframe_columns() -> None:
    runs = [
        make_run(id="run_1", name="baseline", status="completed"),
        make_run(id="run_2", name="hot", status="running"),
    ]
    router = Router().json("GET", r"/v1/runs", page(runs))
    df = make_client(router).runs.to_dataframe()

    assert list(df.columns) == [
        "id",
        "name",
        "status",
        "simulator_type",
        "model_id",
        "sweep_id",
        "created_at",
        "started_at",
        "completed_at",
        "error_message",
    ]
    assert df["id"].tolist() == ["run_1", "run_2"]
    assert df["name"].tolist() == ["baseline", "hot"]
    assert pd.api.types.is_datetime64_any_dtype(df["created_at"])


def test_runs_to_dataframe_empty_has_columns() -> None:
    router = Router().json("GET", r"/v1/runs", page([]))
    df = make_client(router).runs.to_dataframe()
    assert len(df) == 0
    assert "id" in df.columns
    assert "status" in df.columns


def test_runs_to_dataframe_respects_max_rows() -> None:
    runs = [make_run(id=f"run_{i}") for i in range(5)]
    router = Router().json("GET", r"/v1/runs", page(runs, total=5))
    df = make_client(router).runs.to_dataframe(max_rows=2)
    assert len(df) == 2


# --- missing pandas --------------------------------------------------------


def test_to_dataframe_raises_helpful_error_without_pandas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = Router().json(
        "GET",
        r"/v1/sweeps/swp_1/results",
        sweep_results_page([make_sweep_row()]),
    )
    results = make_client(router).sweeps.list_results("swp_1")

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pandas" or name.startswith("pandas."):
            raise ImportError("No module named 'pandas'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.delitem(sys.modules, "pandas", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match=r"pip install ionforge\[pandas\]"):
        results.to_dataframe()


# --- async -----------------------------------------------------------------


def test_async_sweep_list_results_to_dataframe() -> None:
    rows = [make_sweep_row(runId="run_1"), make_sweep_row(runId="run_2")]
    router = Router().json("GET", r"/v1/sweeps/swp_1/results", sweep_results_page(rows))

    async def go() -> pd.DataFrame:
        async with make_async_client(router) as client:
            results = await client.sweeps.list_results("swp_1")
            return results.to_dataframe()

    df = asyncio.run(go())
    assert df["run_id"].tolist() == ["run_1", "run_2"]


def test_async_runs_to_dataframe() -> None:
    runs = [make_run(id="run_1"), make_run(id="run_2")]
    router = Router().json("GET", r"/v1/runs", page(runs))

    async def go() -> pd.DataFrame:
        async with make_async_client(router) as client:
            return await client.runs.to_dataframe()

    df = asyncio.run(go())
    assert df["id"].tolist() == ["run_1", "run_2"]
