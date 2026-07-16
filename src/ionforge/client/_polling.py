"""Polling helpers for long-running runs and sweeps."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ionforge._types._generated import Run, Sweep

if TYPE_CHECKING:
    from ._resources.runs import AsyncRuns, Runs
    from ._resources.sweeps import AsyncSweeps, Sweeps

_TERMINAL_RUN_STATUSES = {"completed", "failed"}
_TERMINAL_SWEEP_STATUSES = {"completed", "failed"}


def poll_run(
    runs: Runs,
    run_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> Run:
    """Poll a run until it reaches a terminal state.

    Raises ``TimeoutError`` if the run does not finish within *timeout* seconds.
    """
    elapsed = 0.0
    while True:
        run = runs.get(run_id)
        if run.status in _TERMINAL_RUN_STATUSES:
            return run
        if elapsed >= timeout:
            raise TimeoutError(f"Run {run_id} still {run.status} after {timeout}s")
        time.sleep(interval)
        elapsed += interval


async def async_poll_run(
    runs: AsyncRuns,
    run_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> Run:
    """Async version of :func:`poll_run`."""
    import asyncio

    elapsed = 0.0
    while True:
        run = await runs.get(run_id)
        if run.status in _TERMINAL_RUN_STATUSES:
            return run
        if elapsed >= timeout:
            raise TimeoutError(f"Run {run_id} still {run.status} after {timeout}s")
        await asyncio.sleep(interval)
        elapsed += interval


def poll_sweep(
    sweeps: Sweeps,
    sweep_id: str,
    *,
    interval: float = 5.0,
    timeout: float = 3600.0,
) -> Sweep:
    """Poll a sweep until it reaches a terminal state.

    Raises ``TimeoutError`` if the sweep does not finish within *timeout* seconds.
    """
    elapsed = 0.0
    while True:
        sweep = sweeps.get(sweep_id)
        if sweep.status in _TERMINAL_SWEEP_STATUSES:
            return sweep
        if elapsed >= timeout:
            raise TimeoutError(
                f"Sweep {sweep_id} still {sweep.status} after {timeout}s"
            )
        time.sleep(interval)
        elapsed += interval


async def async_poll_sweep(
    sweeps: AsyncSweeps,
    sweep_id: str,
    *,
    interval: float = 5.0,
    timeout: float = 3600.0,
) -> Sweep:
    """Async version of :func:`poll_sweep`."""
    import asyncio

    elapsed = 0.0
    while True:
        sweep = await sweeps.get(sweep_id)
        if sweep.status in _TERMINAL_SWEEP_STATUSES:
            return sweep
        if elapsed >= timeout:
            raise TimeoutError(
                f"Sweep {sweep_id} still {sweep.status} after {timeout}s"
            )
        await asyncio.sleep(interval)
        elapsed += interval
