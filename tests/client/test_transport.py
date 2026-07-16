"""Transport-level tests: headers, retries, and error mapping."""

from __future__ import annotations

import httpx
import pytest

from ionforge.client import (
    APIError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from ionforge.client import _transport as transport_mod

from .conftest import Router, make_client, make_project_with_counts


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace the retry backoff sleep with a recorder so tests never block."""
    delays: list[float] = []
    monkeypatch.setattr(transport_mod.time, "sleep", delays.append)
    return delays


def test_auth_and_org_headers_present() -> None:
    router = Router().json("GET", r"/v1/projects/proj_1", make_project_with_counts())
    client = make_client(router, api_key="ifk_secret", org_id="org_42")
    client.projects.get("proj_1")

    req = router.last
    assert req.headers["Authorization"] == "Bearer ifk_secret"
    assert req.headers["X-Org-Id"] == "org_42"


def test_user_agent_reports_package_version() -> None:
    router = Router().json("GET", r"/v1/projects/proj_1", make_project_with_counts())
    client = make_client(router)
    client.projects.get("proj_1")

    ua = router.last.headers["User-Agent"]
    assert ua == transport_mod._USER_AGENT
    assert ua.startswith("ionforge-python/")


def test_session_token_used_when_no_api_key() -> None:
    router = Router().json("GET", r"/v1/projects/proj_1", make_project_with_counts())
    client = make_client(router, api_key=None, session_token="sess_abc")
    client.projects.get("proj_1")
    assert router.last.headers["Authorization"] == "Bearer sess_abc"


def test_org_header_absent_when_not_configured() -> None:
    router = Router().json("GET", r"/v1/projects/proj_1", make_project_with_counts())
    client = make_client(router, org_id=None)
    client.projects.get("proj_1")
    assert "X-Org-Id" not in router.last.headers


def test_get_retries_on_503_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"message": "unavailable"})
        return httpx.Response(200, json=make_project_with_counts())

    client = make_client(Router().add("GET", r"/v1/projects/proj_1", handler))
    client.projects.get("proj_1")
    assert calls["n"] == 2


def test_get_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"message": "slow down"})
        return httpx.Response(200, json=make_project_with_counts())

    client = make_client(Router().add("GET", r"/v1/projects/proj_1", handler))
    client.projects.get("proj_1")
    assert calls["n"] == 2


def test_post_does_not_retry_on_503() -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"message": "unavailable"})

    client = make_client(Router().add("POST", r"/v1/projects", handler))
    with pytest.raises(InternalServerError):
        client.projects.create(name="P")
    assert calls["n"] == 1


def test_retry_after_header_is_honored(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429, json={"message": "slow"}, headers={"Retry-After": "7"}
            )
        return httpx.Response(200, json=make_project_with_counts())

    client = make_client(Router().add("GET", r"/v1/projects/proj_1", handler))
    client.projects.get("proj_1")
    assert 7.0 in _no_sleep


@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (422, APIError),
        (429, RateLimitError),
        (500, InternalServerError),
    ],
)
def test_error_status_maps_to_typed_exception(status: int, exc: type[APIError]) -> None:
    router = Router().add(
        "GET",
        r"/v1/projects/proj_1",
        lambda _req: httpx.Response(status, json={"message": "boom"}),
    )
    client = make_client(router, max_retries=0)
    with pytest.raises(exc) as info:
        client.projects.get("proj_1")
    assert info.value.status_code == status
    assert info.value.message == "boom"


def test_rate_limit_error_exposes_retry_after() -> None:
    router = Router().add(
        "GET",
        r"/v1/projects/proj_1",
        lambda _req: httpx.Response(
            429, json={"message": "slow"}, headers={"Retry-After": "3"}
        ),
    )
    client = make_client(router, max_retries=0)
    with pytest.raises(RateLimitError) as info:
        client.projects.get("proj_1")
    assert info.value.retry_after == 3.0
