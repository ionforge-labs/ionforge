"""Load downloaded run result files into numpy arrays and pandas DataFrames.

:func:`download_results` (and :meth:`IonForge.load_results`) write result files
to disk as JSON documents. This module parses those files into typed Python
objects for analysis: scalar metrics as attributes, per-particle quantities as
numpy arrays, and optional per-particle trajectories.

A downloaded result file is one of two shapes:

* a *summary* document -- the scalar run metrics plus the per-particle exit and
  input arrays; or
* a *full* document -- a ``summary`` block as above, plus a ``trajectories``
  list when the run stored per-particle paths.

:func:`load_result` accepts either shape and tolerates missing or null optional
fields. numpy is a core dependency and is always available; pandas is optional
(the ``pandas`` extra) and imported lazily inside :meth:`RunResultData.to_dataframe`
and :meth:`RunResultData.transmission_curve_dataframe`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from ._dataframe import _require_pandas

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class EnergyResolution:
    """Energy-resolution metrics of the transmitted beam, in electron-volts.

    Any field is ``None`` when the downloaded result file omits it.
    """

    fwhm_eV: float | None = None
    """Full width at half maximum of the exit-energy distribution (eV)."""
    mean_eV: float | None = None
    """Mean exit energy of transmitted particles (eV)."""
    std_eV: float | None = None
    """Standard deviation of the exit energy (eV)."""


@dataclass(frozen=True)
class PSF:
    """Point-spread metrics of the transmitted beam at the exit plane.

    Any field is ``None`` when the downloaded result file omits it.
    """

    mean_x: float | None = None
    """Mean exit position (metres)."""
    std_x: float | None = None
    """Standard deviation of the exit position (metres)."""
    fwhm_x: float | None = None
    """Full width at half maximum of the exit-position distribution (metres)."""


@dataclass(frozen=True)
class ResultSummary:
    """Scalar metrics reported in a downloaded run result file.

    Fields default to ``None`` when the file omits them.
    """

    n_total: int | None = None
    """Number of particles launched."""
    n_transmitted: int | None = None
    """Number of particles that reached the exit plane."""
    transmission: float | None = None
    """Transmitted fraction (``n_transmitted / n_total``), between 0 and 1."""
    energy_resolution: EnergyResolution | None = None
    """Energy-resolution metrics, or ``None`` when absent."""
    psf: PSF | None = None
    """Point-spread metrics at the exit plane, or ``None`` when absent."""


@dataclass(frozen=True)
class Trajectory:
    """A single particle's stored path through the column.

    ``positions`` and ``times`` are ``None`` when the file did not store them
    for this particle.
    """

    transmitted: bool | None = None
    """Whether the particle reached the exit plane."""
    reason: str | None = None
    """Why the particle stopped (e.g. reached the exit, struck an electrode)."""
    n_steps: int | None = None
    """Number of integration steps stored for this particle."""
    positions: np.ndarray | None = None
    """Stored positions as an ``(N, 2)`` float array, or ``None``."""
    times: np.ndarray | None = None
    """Stored step times as a 1-D float array, or ``None``."""


@dataclass(frozen=True)
class RunResultData:
    """Parsed contents of a downloaded run result file.

    Build one with :func:`load_result`. Scalar metrics live on :attr:`summary`;
    per-particle quantities are numpy arrays; per-particle paths (when the file
    stored them) are :class:`Trajectory` objects on :attr:`trajectories`.
    """

    summary: ResultSummary
    """Scalar run metrics (transmission, energy resolution, point spread)."""
    exit_positions: np.ndarray
    """Exit position per transmitted particle (metres); empty when absent."""
    exit_energies: np.ndarray
    """Exit energy per transmitted particle (eV); empty when absent."""
    input_energies: np.ndarray
    """Input energy per launched particle (eV); empty when absent."""
    transmission_curve: tuple[np.ndarray, np.ndarray] | None = None
    """``(energies, transmission)`` arrays of the transmission curve, or ``None``."""
    trajectories: list[Trajectory] = field(default_factory=list)
    """Per-particle stored paths; empty when the file stored none."""
    _present: frozenset[str] = field(default_factory=frozenset, repr=False)
    """Names of the per-particle array fields present in the source file."""

    def to_dataframe(self) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """Assemble the per-particle arrays into a DataFrame.

        The input array holds one value per *launched* particle, while the exit
        arrays hold one value per *transmitted* particle, so their lengths
        differ whenever any particle is lost. Rather than fabricate a per-row
        pairing that would misalign transmitted particles with launched ones,
        this method aligns honestly from the data shape:

        * When the input and exit rows line up 1:1 (equal lengths, e.g. full
          transmission, or only one side present), a single frame is returned
          with the columns that apply: ``input_energy``, ``exit_energy``,
          ``exit_position``.
        * When they differ, a ``{"particles": ..., "exits": ...}`` dict of two
          frames is returned -- ``particles`` (one row per launched particle,
          column ``input_energy``) and ``exits`` (one row per transmitted
          particle, columns ``exit_energy`` and/or ``exit_position``).

        Only columns whose fields were present in the source file appear.
        Requires the ``pandas`` extra.
        """
        pd = _require_pandas()

        exit_cols: dict[str, np.ndarray] = {}
        if "exit_energies" in self._present:
            exit_cols["exit_energy"] = self.exit_energies
        if "exit_positions" in self._present:
            exit_cols["exit_position"] = self.exit_positions
        has_input = "input_energies" in self._present

        n_in = len(self.input_energies) if has_input else None
        exit_lengths = {len(v) for v in exit_cols.values()}
        if len(exit_lengths) > 1:
            raise ValueError(
                "exit arrays have mismatched lengths "
                f"{ {k: len(v) for k, v in exit_cols.items()} }; "
                "the result file is malformed"
            )
        n_exit = exit_lengths.pop() if exit_cols else None

        # Single frame when the two row counts coincide (or one side is absent).
        if n_in is not None and (n_exit is None or n_exit == n_in):
            columns: dict[str, np.ndarray] = {"input_energy": self.input_energies}
            columns.update(exit_cols)
            return pd.DataFrame(columns)
        if n_in is None:
            return pd.DataFrame(exit_cols)

        # Row counts genuinely differ: keep the two tables separate.
        return {
            "particles": pd.DataFrame({"input_energy": self.input_energies}),
            "exits": pd.DataFrame(exit_cols),
        }

    def transmission_curve_dataframe(self) -> pd.DataFrame | None:
        """Return the transmission curve as a two-column DataFrame, or ``None``.

        Columns are ``energy`` and ``transmission``. Returns ``None`` when the
        file carried no transmission curve. Requires the ``pandas`` extra.
        """
        if self.transmission_curve is None:
            return None
        pd = _require_pandas()
        energies, transmission = self.transmission_curve
        return pd.DataFrame({"energy": energies, "transmission": transmission})


def _as_float_array(value: Any) -> np.ndarray:
    """Coerce a JSON list (or ``None``) into a 1-D float array."""
    if value is None:
        return np.asarray([], dtype=float)
    return np.asarray(value, dtype=float)


def _parse_energy_resolution(data: Any) -> EnergyResolution | None:
    if not isinstance(data, dict):
        return None
    return EnergyResolution(
        fwhm_eV=data.get("fwhm_eV"),
        mean_eV=data.get("mean_eV"),
        std_eV=data.get("std_eV"),
    )


def _parse_psf(data: Any) -> PSF | None:
    if not isinstance(data, dict):
        return None
    return PSF(
        mean_x=data.get("mean_x"),
        std_x=data.get("std_x"),
        fwhm_x=data.get("fwhm_x"),
    )


def _parse_transmission_curve(data: Any) -> tuple[np.ndarray, np.ndarray] | None:
    if not isinstance(data, dict):
        return None
    energies = data.get("energies")
    transmission = data.get("transmission")
    if energies is None or transmission is None:
        return None
    return _as_float_array(energies), _as_float_array(transmission)


def _parse_positions(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=float)
    if arr.size == 0:
        return arr.reshape(0, 2)
    return arr


def _parse_trajectory(data: Any) -> Trajectory:
    if not isinstance(data, dict):
        return Trajectory()
    times = data.get("times")
    return Trajectory(
        transmitted=data.get("transmitted"),
        reason=data.get("reason"),
        n_steps=data.get("n_steps"),
        positions=_parse_positions(data.get("positions")),
        times=None if times is None else _as_float_array(times),
    )


def _from_summary(
    summary: dict[str, Any],
) -> tuple[
    ResultSummary,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[np.ndarray, np.ndarray] | None,
    frozenset[str],
]:
    """Parse a summary mapping into its typed pieces and array-presence set."""
    result_summary = ResultSummary(
        n_total=summary.get("n_total"),
        n_transmitted=summary.get("n_transmitted"),
        transmission=summary.get("transmission"),
        energy_resolution=_parse_energy_resolution(summary.get("energy_resolution")),
        psf=_parse_psf(summary.get("psf")),
    )
    present = frozenset(
        key
        for key in ("exit_positions", "exit_energies", "input_energies")
        if summary.get(key) is not None
    )
    return (
        result_summary,
        _as_float_array(summary.get("exit_positions")),
        _as_float_array(summary.get("exit_energies")),
        _as_float_array(summary.get("input_energies")),
        _parse_transmission_curve(summary.get("transmission_curve")),
        present,
    )


def load_result(path: str | Path) -> RunResultData:
    """Load a downloaded run result file into a :class:`RunResultData`.

    Accepts either result-file shape -- a bare summary document or a full
    document with a ``summary`` block and an optional ``trajectories`` list --
    and tolerates missing or null optional fields.

    :param path: Path to a downloaded result file (JSON).
    """
    with open(path, encoding="utf-8") as f:
        document: Any = json.load(f)
    if not isinstance(document, dict):
        raise ValueError(f"result file {path!s} is not a JSON object at the top level")

    inner = document.get("summary")
    if isinstance(inner, dict):
        summary_data = inner
        trajectories_data = document.get("trajectories")
    else:
        summary_data = document
        trajectories_data = None

    (
        summary,
        exit_positions,
        exit_energies,
        input_energies,
        transmission_curve,
        present,
    ) = _from_summary(summary_data)

    trajectories = (
        [_parse_trajectory(t) for t in trajectories_data]
        if isinstance(trajectories_data, list)
        else []
    )

    return RunResultData(
        summary=summary,
        exit_positions=exit_positions,
        exit_energies=exit_energies,
        input_energies=input_energies,
        transmission_curve=transmission_curve,
        trajectories=trajectories,
        _present=present,
    )


__all__ = [
    "EnergyResolution",
    "PSF",
    "ResultSummary",
    "Trajectory",
    "RunResultData",
    "load_result",
]
