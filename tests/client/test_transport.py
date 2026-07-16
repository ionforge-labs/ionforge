"""Transport-level tests: headers, retries, and error mapping."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from ionforge.client import (
    APIError,
    AuthenticationError,
    BadRequestError,
    ConnectionError,
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
    # Exact type, not a subclass: the 422 row must land on the generic
    # APIError, not silently on some narrower subclass.
    assert type(info.value) is exc
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


def test_get_retries_are_exhausted_then_raises(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"message": "still down"})

    max_retries = 3
    client = make_client(
        Router().add("GET", r"/v1/projects/proj_1", handler),
        max_retries=max_retries,
    )
    with pytest.raises(InternalServerError):
        client.projects.get("proj_1")
    # One initial attempt plus one per retry.
    assert calls["n"] == max_retries + 1


def test_connect_error_retries_then_raises_connection_error(
    _no_sleep: list[float],
) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("connection refused")

    max_retries = 2
    client = make_client(
        Router().add("GET", r"/v1/projects/proj_1", handler),
        max_retries=max_retries,
    )
    with pytest.raises(ConnectionError):
        client.projects.get("proj_1")
    # Transport error is retried before the typed ConnectionError surfaces.
    assert calls["n"] == max_retries + 1
    assert len(_no_sleep) == max_retries


def test_post_not_retried_on_read_timeout(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("read timed out")

    client = make_client(
        Router().add("POST", r"/v1/projects", handler),
        max_retries=3,
    )
    with pytest.raises(ConnectionError):
        client.projects.create(name="P")
    # A read-phase failure may mean the POST already reached the server, so it
    # must not be re-sent: exactly one attempt, no backoff sleeps.
    assert calls["n"] == 1
    assert _no_sleep == []


def test_post_retried_on_connect_error(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("connection refused")

    max_retries = 2
    client = make_client(
        Router().add("POST", r"/v1/projects", handler),
        max_retries=max_retries,
    )
    with pytest.raises(ConnectionError):
        client.projects.create(name="P")
    # The connection never reached the server, so re-sending the POST is safe.
    assert calls["n"] == max_retries + 1
    assert len(_no_sleep) == max_retries


def test_get_retried_on_read_timeout(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("read timed out")

    max_retries = 2
    client = make_client(
        Router().add("GET", r"/v1/projects/proj_1", handler),
        max_retries=max_retries,
    )
    with pytest.raises(ConnectionError):
        client.projects.get("proj_1")
    # GET is idempotent, so a read timeout is retried like any transport error.
    assert calls["n"] == max_retries + 1
    assert len(_no_sleep) == max_retries


def test_non_json_error_body_falls_back_to_text() -> None:
    router = Router().add(
        "GET",
        r"/v1/projects/proj_1",
        lambda _req: httpx.Response(500, text="<html>oops"),
    )
    client = make_client(router, max_retries=0)
    with pytest.raises(InternalServerError) as info:
        client.projects.get("proj_1")
    # No JSON body to read a message from, so the raw text is used.
    assert info.value.message == "<html>oops"


def test_post_retried_on_pool_timeout(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.PoolTimeout("pool exhausted")

    max_retries = 2
    client = make_client(
        Router().add("POST", r"/v1/projects", handler),
        max_retries=max_retries,
    )
    with pytest.raises(ConnectionError):
        client.projects.create(name="P")
    # No connection was ever acquired, so the POST never left the client and is
    # safe to retry despite being a mutating method.
    assert calls["n"] == max_retries + 1
    assert len(_no_sleep) == max_retries


# --- presigned streaming (SyncTransport.stream_to_file) --------------------


def test_stream_to_file_follows_redirect(tmp_path: Path) -> None:
    router = (
        Router()
        .add(
            "GET",
            r"/presigned",
            lambda _r: httpx.Response(
                307, headers={"location": "https://storage.example.com/blob"}
            ),
        )
        .add("GET", r"/blob", lambda _r: httpx.Response(200, content=b"payload"))
    )
    client = make_client(router)
    dest = tmp_path / "f"
    client._transport.stream_to_file("https://files.example.com/presigned", dest)
    # Presigned links 307 to storage; a bare httpx.stream (follow_redirects off)
    # would fail here, but the transport client follows the redirect.
    assert dest.read_bytes() == b"payload"


def test_stream_to_file_maps_terminal_status_to_typed_exception(
    tmp_path: Path,
) -> None:
    router = Router().add(
        "GET", r"/missing", lambda _r: httpx.Response(404, json={"message": "gone"})
    )
    client = make_client(router, max_retries=0)
    with pytest.raises(NotFoundError):
        client._transport.stream_to_file(
            "https://files.example.com/missing", tmp_path / "f"
        )


def test_stream_to_file_sends_no_authorization_header(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, content=b"x")

    client = make_client(Router().add("GET", r"/f", handler), api_key="ifk_secret")
    client._transport.stream_to_file("https://files.example.com/f", tmp_path / "f")
    # The API credential must never be forwarded to a third-party storage host.
    assert "authorization" not in {k.lower() for k in seen[0].headers}
    assert seen[0].headers["user-agent"] == transport_mod._USER_AGENT


def test_stream_client_uses_configured_timeout() -> None:
    client = make_client(Router(), timeout=12.5)
    # The download client inherits the client timeout, not httpx's 5s default.
    assert client._transport._stream_client.timeout.read == 12.5
    assert client._transport._stream_client.timeout.connect == 12.5


def test_stream_to_file_retries_on_503(_no_sleep: list[float], tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"message": "down"})
        return httpx.Response(200, content=b"ok")

    client = make_client(Router().add("GET", r"/f", handler))
    dest = tmp_path / "f"
    client._transport.stream_to_file("https://files.example.com/f", dest)
    assert calls["n"] == 2
    assert dest.read_bytes() == b"ok"


def test_stream_to_file_success_leaves_only_complete_dest(tmp_path: Path) -> None:
    router = Router().add(
        "GET", r"/f", lambda _r: httpx.Response(200, content=b"complete-payload")
    )
    client = make_client(router)
    dest = tmp_path / "result.h5"
    client._transport.stream_to_file("https://files.example.com/f", dest)
    # The finished file is present with its full contents and no ``.part`` residue.
    assert dest.read_bytes() == b"complete-payload"
    assert [p.name for p in tmp_path.iterdir()] == ["result.h5"]


def test_stream_to_file_terminal_status_leaves_no_file(tmp_path: Path) -> None:
    router = Router().add(
        "GET", r"/missing", lambda _r: httpx.Response(404, json={"message": "gone"})
    )
    client = make_client(router, max_retries=0)
    dest = tmp_path / "result.h5"
    with pytest.raises(NotFoundError):
        client._transport.stream_to_file("https://files.example.com/missing", dest)
    # No dest and no ``.part`` temp are left behind on a terminal HTTP error.
    assert list(tmp_path.iterdir()) == []


def test_stream_to_file_midstream_failure_leaves_no_file(
    _no_sleep: list[float], tmp_path: Path
) -> None:
    def body() -> Iterator[bytes]:
        yield b"partial-bytes-"
        raise httpx.ReadError("connection dropped mid-stream")

    router = Router().add("GET", r"/f", lambda _r: httpx.Response(200, content=body()))
    client = make_client(router, max_retries=0)
    dest = tmp_path / "result.h5"
    with pytest.raises(ConnectionError):
        client._transport.stream_to_file("https://files.example.com/f", dest)
    # A failure after some bytes were written must leave neither a truncated
    # dest file nor the ``.part`` temp.
    assert list(tmp_path.iterdir()) == []


def test_non_numeric_retry_after_is_ignored(_no_sleep: list[float]) -> None:
    calls = {"n": 0}

    def handler(_req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                json={"message": "slow"},
                headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
            )
        return httpx.Response(200, json=make_project_with_counts())

    client = make_client(Router().add("GET", r"/v1/projects/proj_1", handler))
    # An RFC-1123 date form must not crash; it is treated as absent so the
    # backoff falls through to the exponential schedule.
    client.projects.get("proj_1")
    assert calls["n"] == 2
    assert _no_sleep == [transport_mod._backoff_delay(0, None)]
