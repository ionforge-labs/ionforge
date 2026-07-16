"""Polling helpers for long-running runs and sweeps."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from ionforge._types._generated import Run, Sweep

if TYPE_CHECKING:
    from ._resources.runs import AsyncRuns, Runs
    from ._resources.sweeps import AsyncSweeps, Sweeps

# A single terminal-status set covers both runs and sweeps; their lifecycles
# share the same three end states.
_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

_T = TypeVar("_T")


def _check_interval(interval: float) -> None:
    """Reject a non-positive poll interval rather than silently busy-looping."""
    if interval <= 0:
        raise ValueError(f"interval must be positive, got {interval!r}")


def _poll(
    get: Callable[[], _T],
    status_of: Callable[[_T], str],
    label: str,
    resource_id: str,
    *,
    interval: float,
    timeout: float,
) -> _T:
    """Poll ``get`` until its result reaches a terminal status or *timeout*.

    The deadline is measured against a wall clock (``time.monotonic``) so the
    total wait honours *timeout* regardless of how long each ``get`` call takes,
    rather than accumulating idealised interval ticks.
    """
    _check_interval(interval)
    deadline = time.monotonic() + timeout
    while True:
        resource = get()
        status = status_of(resource)
        if status in _TERMINAL_STATUSES:
            return resource
        if time.monotonic() >= deadline:
            raise TimeoutError(f"{label} {resource_id} still {status} after {timeout}s")
        time.sleep(interval)


async def _async_poll(
    get: Callable[[], Awaitable[_T]],
    status_of: Callable[[_T], str],
    label: str,
    resource_id: str,
    *,
    interval: float,
    timeout: float,
) -> _T:
    """Async counterpart to :func:`_poll`."""
    _check_interval(interval)
    deadline = time.monotonic() + timeout
    while True:
        resource = await get()
        status = status_of(resource)
        if status in _TERMINAL_STATUSES:
            return resource
        if time.monotonic() >= deadline:
            raise TimeoutError(f"{label} {resource_id} still {status} after {timeout}s")
        await asyncio.sleep(interval)


def poll_run(
    runs: Runs,
    run_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> Run:
    """Poll a run until it reaches a terminal state.

    Raises ``TimeoutError`` if the run does not finish within *timeout* seconds,
    and ``ValueError`` if *interval* is not positive.
    """
    return _poll(
        lambda: runs.get(run_id),
        lambda run: run.status,
        "Run",
        run_id,
        interval=interval,
        timeout=timeout,
    )


async def async_poll_run(
    runs: AsyncRuns,
    run_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> Run:
    """Async version of :func:`poll_run`.

    Raises ``TimeoutError`` if the run does not finish within *timeout* seconds,
    and ``ValueError`` if *interval* is not positive.
    """
    return await _async_poll(
        lambda: runs.get(run_id),
        lambda run: run.status,
        "Run",
        run_id,
        interval=interval,
        timeout=timeout,
    )


def poll_sweep(
    sweeps: Sweeps,
    sweep_id: str,
    *,
    interval: float = 5.0,
    timeout: float = 3600.0,
) -> Sweep:
    """Poll a sweep until it reaches a terminal state.

    Raises ``TimeoutError`` if the sweep does not finish within *timeout*
    seconds, and ``ValueError`` if *interval* is not positive.
    """
    return _poll(
        lambda: sweeps.get(sweep_id),
        lambda sweep: sweep.status,
        "Sweep",
        sweep_id,
        interval=interval,
        timeout=timeout,
    )


async def async_poll_sweep(
    sweeps: AsyncSweeps,
    sweep_id: str,
    *,
    interval: float = 5.0,
    timeout: float = 3600.0,
) -> Sweep:
    """Async version of :func:`poll_sweep`.

    Raises ``TimeoutError`` if the sweep does not finish within *timeout*
    seconds, and ``ValueError`` if *interval* is not positive.
    """
    return await _async_poll(
        lambda: sweeps.get(sweep_id),
        lambda sweep: sweep.status,
        "Sweep",
        sweep_id,
        interval=interval,
        timeout=timeout,
    )
