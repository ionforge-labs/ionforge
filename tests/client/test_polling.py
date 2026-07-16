"""Polling tests: terminal detection and timeout behaviour."""

from __future__ import annotations

import httpx
import pytest

from ionforge.client import _polling as polling_mod
from ionforge.client import poll_run, poll_sweep

from .conftest import Router, make_client, make_run, make_sweep


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(polling_mod.time, "sleep", lambda _s: None)


@pytest.mark.parametrize("terminal", ["completed", "failed", "cancelled"])
def test_poll_run_returns_on_terminal_status(terminal: str) -> None:
    router = Router().json("GET", r"/v1/runs/run_1", make_run(status=terminal))
    client = make_client(router)
    run = poll_run(client.runs, "run_1", interval=0.01, timeout=1.0)
    assert run.status == terminal


def test_poll_run_polls_until_terminal() -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        status = "completed" if calls["n"] >= 3 else "running"
        return httpx.Response(200, json=make_run(status=status))

    client = make_client(Router().add("GET", r"/v1/runs/run_1", handler))
    run = poll_run(client.runs, "run_1", interval=0.01, timeout=10.0)
    assert run.status == "completed"
    assert calls["n"] == 3


def test_poll_run_times_out_when_stuck() -> None:
    router = Router().json("GET", r"/v1/runs/run_1", make_run(status="running"))
    client = make_client(router)
    with pytest.raises(TimeoutError, match="still running"):
        poll_run(client.runs, "run_1", interval=0.01, timeout=0.0)


def test_poll_run_rejects_nonpositive_interval() -> None:
    router = Router().json("GET", r"/v1/runs/run_1", make_run(status="running"))
    client = make_client(router)
    with pytest.raises(ValueError, match="interval must be positive"):
        poll_run(client.runs, "run_1", interval=0.0, timeout=1.0)


def test_poll_run_honours_wall_clock_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A slow get() must not let the total wait overshoot the stated timeout:
    # the deadline is measured against the clock, not by summing intervals.
    router = Router().json("GET", r"/v1/runs/run_1", make_run(status="running"))
    client = make_client(router)

    # Each monotonic() reading advances 5s, so the second check (after one
    # non-terminal poll) is already past a 3s timeout.
    ticks = iter([0.0, 5.0, 10.0, 15.0])
    monkeypatch.setattr(polling_mod.time, "monotonic", lambda: next(ticks))

    with pytest.raises(TimeoutError, match="still running after 3.0s"):
        poll_run(client.runs, "run_1", interval=1.0, timeout=3.0)


@pytest.mark.parametrize("terminal", ["completed", "failed", "cancelled"])
def test_poll_sweep_returns_on_terminal_status(terminal: str) -> None:
    router = Router().json("GET", r"/v1/sweeps/swp_1", make_sweep(status=terminal))
    client = make_client(router)
    sweep = poll_sweep(client.sweeps, "swp_1", interval=0.01, timeout=1.0)
    assert sweep.status == terminal


def test_poll_sweep_times_out_when_stuck() -> None:
    router = Router().json("GET", r"/v1/sweeps/swp_1", make_sweep(status="running"))
    client = make_client(router)
    with pytest.raises(TimeoutError, match="still running"):
        poll_sweep(client.sweeps, "swp_1", interval=0.01, timeout=0.0)
