"""pandas DataFrame accessors for tabular result collections.

pandas is an optional dependency, installed via the ``pandas`` extra
(``pip install ionforge[pandas]``). It is imported lazily inside the accessors
so the rest of the client works without it, and callers who do not touch these
helpers never pay the import cost.
"""

from __future__ import annotations

from collections.abc import Iterable
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from ionforge._types._generated import Row, Row1, Run


def _require_pandas() -> ModuleType:
    """Import pandas or raise a helpful error naming the extra."""
    try:
        import pandas
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise ImportError(
            "DataFrame accessors require pandas. "
            "Install it with: pip install ionforge[pandas]"
        ) from exc
    return pandas


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a (possibly nested) mapping into dot-path keys.

    Sweep points and result summaries arrive as flat ``{dot.path: value}``
    records, but nested mappings are flattened defensively so a ``{"beam":
    {"E_nominal": 1000}}`` shape yields a ``beam.E_nominal`` column too.
    """
    out: dict[str, Any] = {}
    if not isinstance(value, dict):
        return out
    for key, val in value.items():
        col = f"{prefix}{key}"
        if isinstance(val, dict):
            out.update(_flatten(val, prefix=f"{col}."))
        else:
            out[col] = val
    return out


def _coerce_datetimes(df: pd.DataFrame, columns: Iterable[str], pd: ModuleType) -> None:
    """Coerce timestamp columns to timezone-aware datetime dtype, in place."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)


# ---------------------------------------------------------------------------
# Sweep per-point results
# ---------------------------------------------------------------------------

# Point-identity and status columns present on every sweep row, in order.
_SWEEP_BASE_COLUMNS = [
    "run_id",
    "status",
    "objective",
    "completed_at",
    "duration_seconds",
    "error",
]


def _sweep_row_record(row: Row | Row1) -> dict[str, Any]:
    """Turn a sweep results row into a flat record.

    Swept parameter values are flattened by their dot-path (``beam.E_nominal``);
    ``full``-mode result-summary metrics are flattened under a ``summary.``
    prefix so they never collide with a swept-parameter column.
    """
    record: dict[str, Any] = {
        "run_id": row.run_id,
        "status": row.status,
        "objective": row.objective,
        "completed_at": row.completed_at,
        "duration_seconds": row.duration_seconds,
        "error": row.error,
    }
    for col, val in _flatten(row.sweep_point or {}).items():
        record[col] = val
    summary = getattr(row, "result_summary", None)
    for col, val in _flatten(summary or {}).items():
        record[f"summary.{col}"] = val
    return record


def sweep_rows_to_dataframe(rows: list[Row | Row1]) -> pd.DataFrame:
    """Assemble sweep-point rows into a DataFrame with stable column ordering.

    Columns are: the base point/status columns, then the swept-parameter
    columns (sorted by dot-path), then any ``summary.*`` metric columns
    (sorted). An empty ``rows`` list yields an empty frame that still carries
    the base columns.
    """
    pd = _require_pandas()
    records = [_sweep_row_record(row) for row in rows]

    param_cols: list[str] = []
    summary_cols: list[str] = []
    seen = set(_SWEEP_BASE_COLUMNS)
    for record in records:
        for col in record:
            if col in seen:
                continue
            seen.add(col)
            if col.startswith("summary."):
                summary_cols.append(col)
            else:
                param_cols.append(col)

    columns = _SWEEP_BASE_COLUMNS + sorted(param_cols) + sorted(summary_cols)
    df = pd.DataFrame(records, columns=columns)
    _coerce_datetimes(df, ["completed_at"], pd)
    return df


class SweepResults:
    """All per-point results of a sweep, assembled across cursor pages.

    Returned by :meth:`Sweeps.list_results`. Iterable over the underlying rows;
    call :meth:`to_dataframe` for a pandas frame (one row per sweep point).
    """

    def __init__(self, *, rows: list[Row | Row1], mode: str, total_count: int) -> None:
        self.rows = rows
        """The assembled per-point rows (``Row`` for table mode, ``Row1`` for full)."""
        self.mode = mode
        """The result mode the rows were fetched in (``"table"`` or ``"full"``)."""
        self.total_count = total_count
        """Server-reported total number of points in the sweep."""

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Any:
        return iter(self.rows)

    def to_dataframe(self) -> pd.DataFrame:
        """Return a DataFrame with one row per assembled sweep point.

        Requires the ``pandas`` extra.
        """
        return sweep_rows_to_dataframe(self.rows)


# ---------------------------------------------------------------------------
# Run listings
# ---------------------------------------------------------------------------

# Tabular columns projected from each ``Run`` model, in order.
_RUN_COLUMNS = [
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


def _run_record(run: Run) -> dict[str, Any]:
    return {
        "id": run.id,
        "name": run.name,
        "status": run.status,
        "simulator_type": run.simulator_type,
        "model_id": run.model_id,
        "sweep_id": run.sweep_id,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "error_message": run.error_message,
    }


def runs_to_dataframe(runs: Iterable[Run]) -> pd.DataFrame:
    """Assemble runs into a DataFrame with one row per run.

    An empty iterable yields an empty frame that still carries the columns.
    Requires the ``pandas`` extra.
    """
    pd = _require_pandas()
    records = [_run_record(run) for run in runs]
    df = pd.DataFrame(records, columns=_RUN_COLUMNS)
    _coerce_datetimes(df, ["created_at", "started_at", "completed_at"], pd)
    return df
