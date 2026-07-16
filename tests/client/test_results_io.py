"""Tests for the downloaded-result-file loaders in ``ionforge.client.results_io``.

Parsing tests build fixture JSON files under ``tmp_path``; the ``load_results``
convenience test drives the real client stack against an ``httpx.MockTransport``
and rounds a JSON result body through download + parse.
"""

from __future__ import annotations

import asyncio
import builtins
import json
import sys
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

from ionforge.client import load_result
from ionforge.client.results_io import RunResultData

from .conftest import Router, make_async_client, make_client, make_result, page


def _summary(**over: object) -> dict[str, object]:
    """A full summary document; override or drop fields per test."""
    body: dict[str, object] = {
        "n_total": 10,
        "n_transmitted": 7,
        "transmission": 0.7,
        "exit_positions": [0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007],
        "exit_energies": [990.0, 991.0, 992.0, 993.0, 994.0, 995.0, 996.0],
        "input_energies": [1000.0] * 10,
        "energy_resolution": {"fwhm_eV": 2.5, "mean_eV": 993.0, "std_eV": 1.1},
        "psf": {"mean_x": 0.004, "std_x": 0.002, "fwhm_x": 0.0047},
        "transmission_curve": {
            "energies": [980.0, 990.0, 1000.0],
            "transmission": [0.5, 0.7, 0.9],
        },
    }
    body.update(over)
    return body


def _write(tmp_path: Path, document: object, name: str = "result.json") -> Path:
    dest = tmp_path / name
    dest.write_text(json.dumps(document), encoding="utf-8")
    return dest


# --- document shapes -------------------------------------------------------


def test_load_bare_summary_document(tmp_path: Path) -> None:
    data = load_result(_write(tmp_path, _summary()))
    assert isinstance(data, RunResultData)
    assert data.summary.n_total == 10
    assert data.summary.n_transmitted == 7
    assert data.summary.transmission == 0.7
    assert data.summary.energy_resolution is not None
    assert data.summary.energy_resolution.fwhm_eV == 2.5
    assert data.summary.psf is not None
    assert data.summary.psf.fwhm_x == 0.0047
    assert isinstance(data.exit_energies, np.ndarray)
    assert data.exit_energies.shape == (7,)
    assert data.input_energies.shape == (10,)
    assert data.trajectories == []


def test_load_full_document_with_trajectories(tmp_path: Path) -> None:
    document = {
        "summary": _summary(),
        "trajectories": [
            {
                "transmitted": True,
                "reason": "reached_exit",
                "n_steps": 3,
                "positions": [[0.0, 0.0], [0.01, 0.001], [0.02, 0.002]],
                "times": [0.0, 1e-9, 2e-9],
            },
            {"transmitted": False, "reason": "hit_electrode", "n_steps": 1},
        ],
    }
    data = load_result(_write(tmp_path, document))
    assert data.summary.n_total == 10
    assert len(data.trajectories) == 2

    first = data.trajectories[0]
    assert first.transmitted is True
    assert first.reason == "reached_exit"
    assert first.n_steps == 3
    assert first.positions is not None
    assert first.positions.shape == (3, 2)
    assert first.times is not None
    assert first.times.shape == (3,)

    second = data.trajectories[1]
    assert second.transmitted is False
    assert second.positions is None
    assert second.times is None


def test_load_accepts_str_path(tmp_path: Path) -> None:
    path = _write(tmp_path, _summary())
    data = load_result(str(path))
    assert data.summary.n_total == 10


def test_load_rejects_non_object_top_level(tmp_path: Path) -> None:
    path = _write(tmp_path, [1, 2, 3])
    with pytest.raises(ValueError, match="not a JSON object"):
        load_result(path)


# --- non-finite JSON literals ----------------------------------------------


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_load_rejects_non_finite_scalar(tmp_path: Path, literal: str) -> None:
    # json.dumps won't emit these, so write the raw literal into the document.
    path = tmp_path / "result.json"
    path.write_text(f'{{"transmission": {literal}}}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON literal"):
        load_result(path)


def test_load_rejects_non_finite_inside_array(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text('{"exit_energies": [990.0, NaN, 992.0]}', encoding="utf-8")
    with pytest.raises(ValueError, match="NaN"):
        load_result(path)


# --- loud scalar coercion --------------------------------------------------


def test_string_int_scalar_raises_naming_field(tmp_path: Path) -> None:
    path = _write(tmp_path, _summary(n_total="0.7"))
    with pytest.raises((ValueError, TypeError), match="n_total"):
        load_result(path)


def test_string_transmission_raises_naming_field(tmp_path: Path) -> None:
    path = _write(tmp_path, _summary(transmission="not-a-number"))
    with pytest.raises((ValueError, TypeError), match="transmission"):
        load_result(path)


def test_non_numeric_energy_resolution_field_raises_naming_field(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, _summary(energy_resolution={"fwhm_eV": "wide"}))
    with pytest.raises((ValueError, TypeError), match="energy_resolution.fwhm_eV"):
        load_result(path)


def test_scalar_coercion_normalises_numeric_strings(tmp_path: Path) -> None:
    # A parseable numeric string is coerced to a real number, not left as str.
    path = _write(tmp_path, _summary(n_total="10", transmission="0.7"))
    data = load_result(path)
    assert data.summary.n_total == 10
    assert isinstance(data.summary.n_total, int)
    assert data.summary.transmission == 0.7
    assert isinstance(data.summary.transmission, float)


# --- trajectory position shape validation ----------------------------------


def test_positions_accept_three_columns(tmp_path: Path) -> None:
    document = {
        "summary": _summary(),
        "trajectories": [
            {
                "transmitted": True,
                "n_steps": 2,
                "positions": [[0.0, 0.0, 0.0], [0.01, 0.001, 0.002]],
            }
        ],
    }
    data = load_result(_write(tmp_path, document))
    traj = data.trajectories[0]
    assert traj.positions is not None
    assert traj.positions.shape == (2, 3)


def test_positions_reject_one_dimensional(tmp_path: Path) -> None:
    document = {
        "summary": _summary(),
        "trajectories": [{"transmitted": True, "positions": [0.0, 0.1, 0.2]}],
    }
    with pytest.raises(ValueError, match="2 or 3 columns"):
        load_result(_write(tmp_path, document))


def test_positions_reject_four_columns(tmp_path: Path) -> None:
    document = {
        "summary": _summary(),
        "trajectories": [{"transmitted": True, "positions": [[0.0, 0.0, 0.0, 0.0]]}],
    }
    with pytest.raises(ValueError, match=r"shape \(1, 4\)"):
        load_result(_write(tmp_path, document))


# --- missing optionals -----------------------------------------------------


def test_missing_optionals_are_tolerated(tmp_path: Path) -> None:
    document = {
        "n_total": 5,
        "transmission": None,
        "energy_resolution": None,
        "psf": None,
        "transmission_curve": None,
    }
    data = load_result(_write(tmp_path, document))
    assert data.summary.n_total == 5
    assert data.summary.n_transmitted is None
    assert data.summary.transmission is None
    assert data.summary.energy_resolution is None
    assert data.summary.psf is None
    assert data.transmission_curve is None
    # Absent per-particle arrays become empty float arrays.
    assert data.exit_positions.shape == (0,)
    assert data.exit_energies.shape == (0,)
    assert data.input_energies.shape == (0,)


def test_empty_document_yields_all_none(tmp_path: Path) -> None:
    data = load_result(_write(tmp_path, {}))
    assert data.summary.n_total is None
    assert data.transmission_curve is None
    assert data.trajectories == []


def test_partial_energy_resolution(tmp_path: Path) -> None:
    document = _summary(energy_resolution={"fwhm_eV": 3.0})
    data = load_result(_write(tmp_path, document))
    assert data.summary.energy_resolution is not None
    assert data.summary.energy_resolution.fwhm_eV == 3.0
    assert data.summary.energy_resolution.mean_eV is None


def test_empty_positions_reshaped_to_two_columns(tmp_path: Path) -> None:
    document = {
        "summary": _summary(),
        "trajectories": [
            {"transmitted": True, "n_steps": 0, "positions": [], "times": []}
        ],
    }
    data = load_result(_write(tmp_path, document))
    traj = data.trajectories[0]
    assert traj.positions is not None
    assert traj.positions.shape == (0, 2)
    assert traj.times is not None
    assert traj.times.shape == (0,)


# --- to_dataframe alignment ------------------------------------------------


def test_to_dataframe_splits_when_lengths_differ(tmp_path: Path) -> None:
    data = load_result(_write(tmp_path, _summary()))  # 10 launched, 7 transmitted
    frames = data.to_dataframe()
    assert isinstance(frames, dict)
    assert set(frames) == {"particles", "exits"}
    assert list(frames["particles"].columns) == ["input_energy"]
    assert len(frames["particles"]) == 10
    assert set(frames["exits"].columns) == {"exit_energy", "exit_position"}
    assert len(frames["exits"]) == 7


def test_to_dataframe_single_frame_when_all_transmitted(tmp_path: Path) -> None:
    document = _summary(
        n_total=3,
        n_transmitted=3,
        input_energies=[1000.0, 1000.0, 1000.0],
        exit_energies=[990.0, 991.0, 992.0],
        exit_positions=[0.001, 0.002, 0.003],
    )
    data = load_result(_write(tmp_path, document))
    df = data.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["input_energy", "exit_energy", "exit_position"]
    assert len(df) == 3


def test_to_dataframe_only_input_present(tmp_path: Path) -> None:
    document = {"input_energies": [1000.0, 1001.0]}
    data = load_result(_write(tmp_path, document))
    df = data.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["input_energy"]
    assert len(df) == 2


def test_to_dataframe_only_exits_present(tmp_path: Path) -> None:
    document = {"exit_energies": [990.0, 991.0], "exit_positions": [0.001, 0.002]}
    data = load_result(_write(tmp_path, document))
    df = data.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == {"exit_energy", "exit_position"}
    assert len(df) == 2


def test_to_dataframe_omits_absent_exit_column(tmp_path: Path) -> None:
    # exit_energies present (5 transmitted), exit_positions absent.
    document = {
        "input_energies": [1000.0] * 8,
        "exit_energies": [990.0, 991.0, 992.0, 993.0, 994.0],
    }
    data = load_result(_write(tmp_path, document))
    frames = data.to_dataframe()
    assert isinstance(frames, dict)
    assert list(frames["exits"].columns) == ["exit_energy"]
    assert len(frames["exits"]) == 5


def test_to_dataframe_raises_on_mismatched_exit_arrays(tmp_path: Path) -> None:
    document = {
        "exit_energies": [990.0, 991.0, 992.0],
        "exit_positions": [0.001, 0.002],
    }
    data = load_result(_write(tmp_path, document))
    with pytest.raises(ValueError, match="mismatched lengths"):
        data.to_dataframe()


# --- stable dataframe accessors --------------------------------------------


def test_stable_accessors_on_lossy_run(tmp_path: Path) -> None:
    # 10 launched, 7 transmitted -- to_dataframe() would return a dict here.
    data = load_result(_write(tmp_path, _summary()))
    assert isinstance(data.to_dataframe(), dict)

    particles = data.particles_dataframe()
    assert isinstance(particles, pd.DataFrame)
    assert list(particles.columns) == ["input_energy"]
    assert len(particles) == 10

    exits = data.exits_dataframe()
    assert isinstance(exits, pd.DataFrame)
    assert set(exits.columns) == {"exit_energy", "exit_position"}
    assert len(exits) == 7


def test_stable_accessors_on_lossless_run(tmp_path: Path) -> None:
    document = _summary(
        n_total=3,
        n_transmitted=3,
        input_energies=[1000.0, 1000.0, 1000.0],
        exit_energies=[990.0, 991.0, 992.0],
        exit_positions=[0.001, 0.002, 0.003],
    )
    data = load_result(_write(tmp_path, document))
    # The adaptive accessor collapses to a single frame here.
    assert isinstance(data.to_dataframe(), pd.DataFrame)

    # The stable accessors keep the two tables separate regardless.
    particles = data.particles_dataframe()
    assert list(particles.columns) == ["input_energy"]
    assert len(particles) == 3

    exits = data.exits_dataframe()
    assert set(exits.columns) == {"exit_energy", "exit_position"}
    assert len(exits) == 3


def test_stable_accessors_shape_is_invariant_across_runs(tmp_path: Path) -> None:
    # Same columns whether the run is lossy or lossless -- no type/shape flip.
    lossy = load_result(_write(tmp_path, _summary(), name="lossy.json"))
    lossless = load_result(
        _write(
            tmp_path,
            _summary(
                n_total=3,
                n_transmitted=3,
                input_energies=[1000.0, 1000.0, 1000.0],
                exit_energies=[990.0, 991.0, 992.0],
                exit_positions=[0.001, 0.002, 0.003],
            ),
            name="lossless.json",
        )
    )
    assert (
        list(lossy.particles_dataframe().columns)
        == list(lossless.particles_dataframe().columns)
        == ["input_energy"]
    )
    assert set(lossy.exits_dataframe().columns) == set(
        lossless.exits_dataframe().columns
    )


def test_exits_dataframe_raises_on_mismatched_exit_arrays(tmp_path: Path) -> None:
    document = {
        "exit_energies": [990.0, 991.0, 992.0],
        "exit_positions": [0.001, 0.002],
    }
    data = load_result(_write(tmp_path, document))
    with pytest.raises(ValueError, match="mismatched lengths"):
        data.exits_dataframe()


# --- transmission_curve_dataframe ------------------------------------------


def test_transmission_curve_dataframe(tmp_path: Path) -> None:
    data = load_result(_write(tmp_path, _summary()))
    curve = data.transmission_curve_dataframe()
    assert curve is not None
    assert list(curve.columns) == ["energy", "transmission"]
    assert len(curve) == 3


def test_transmission_curve_dataframe_none_when_absent(tmp_path: Path) -> None:
    data = load_result(_write(tmp_path, _summary(transmission_curve=None)))
    assert data.transmission_curve is None
    assert data.transmission_curve_dataframe() is None


# --- missing pandas --------------------------------------------------------


def test_to_dataframe_raises_helpful_error_without_pandas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = load_result(_write(tmp_path, _summary()))

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pandas" or name.startswith("pandas."):
            raise ImportError("No module named 'pandas'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.delitem(sys.modules, "pandas", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match=r"pip install ionforge\[pandas\]"):
        data.to_dataframe()


# --- load_results convenience over the client --------------------------------

_PRESIGNED_URL = "https://files.example.com/results/res_1?sig=opaque"


def _download_router(body: dict[str, object]) -> Router:
    def presigned(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(body).encode("utf-8"))

    return (
        Router()
        .json("GET", r"/v1/runs/run_1/results", page([make_result(id="res_1")]))
        .json("GET", r"/v1/runs/run_1/results/res_1/download", {"url": _PRESIGNED_URL})
        .add("GET", r"/results/res_1", presigned)
    )


def test_load_results_sync_download_and_parse(tmp_path: Path) -> None:
    client = make_client(_download_router(_summary()))
    results = client.load_results("run_1", output_dir=tmp_path)

    assert len(results) == 1
    assert isinstance(results[0], RunResultData)
    assert results[0].summary.n_transmitted == 7
    assert results[0].exit_energies.shape == (7,)


def test_load_results_async_download_and_parse(tmp_path: Path) -> None:
    async def go() -> list[RunResultData]:
        client = make_async_client(_download_router(_summary()))
        results = await client.load_results("run_1", output_dir=tmp_path)
        await client.close()
        return results

    results = asyncio.run(go())
    assert len(results) == 1
    assert results[0].summary.transmission == 0.7
