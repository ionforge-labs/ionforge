"""Polling helpers for long-running jobs and sweeps."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ._generated import Job, Sweep

if TYPE_CHECKING:
    from ._resources.jobs import AsyncJobs, Jobs
    from ._resources.sweeps import AsyncSweeps, Sweeps

_TERMINAL_JOB_STATUSES = {"completed", "failed"}
_TERMINAL_SWEEP_STATUSES = {"completed", "failed"}


def poll_job(
    jobs: Jobs,
    job_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> Job:
    """Poll a job until it reaches a terminal state.

    Raises ``TimeoutError`` if the job does not finish within *timeout* seconds.
    """
    elapsed = 0.0
    while True:
        job = jobs.get(job_id)
        if job.status in _TERMINAL_JOB_STATUSES:
            return job
        if elapsed >= timeout:
            raise TimeoutError(f"Job {job_id} still {job.status} after {timeout}s")
        time.sleep(interval)
        elapsed += interval


async def async_poll_job(
    jobs: AsyncJobs,
    job_id: str,
    *,
    interval: float = 2.0,
    timeout: float = 600.0,
) -> Job:
    """Async version of :func:`poll_job`."""
    import asyncio

    elapsed = 0.0
    while True:
        job = await jobs.get(job_id)
        if job.status in _TERMINAL_JOB_STATUSES:
            return job
        if elapsed >= timeout:
            raise TimeoutError(f"Job {job_id} still {job.status} after {timeout}s")
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
