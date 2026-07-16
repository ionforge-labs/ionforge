"""HTTP transport layer wrapping httpx with retry, auth headers, and error mapping."""

from __future__ import annotations

import asyncio
import time
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx

from ._config import ClientConfig
from ._exceptions import (
    ConnectionError,
    RateLimitError,
    _exception_for_status,
)

# Version reported in the User-Agent, resolved from the installed package
# metadata with a fallback for editable or unpackaged checkouts.
_FALLBACK_VERSION = "0.0.0"
try:
    _VERSION = version("ionforge")
except PackageNotFoundError:  # pragma: no cover - unpackaged checkout
    _VERSION = _FALLBACK_VERSION
_USER_AGENT = f"ionforge-python/{_VERSION}"

# Status codes that trigger automatic retry.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# HTTP methods considered safe to retry (idempotent).
_RETRYABLE_METHODS = {"GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def _parse_retry_after(raw: str | None) -> float | None:
    """Parse a ``Retry-After`` header value into seconds.

    The header may carry either a number of seconds or an HTTP-date
    (RFC 1123). Only the numeric form is honoured; anything non-numeric
    (including a date) is treated as absent so the caller falls back to
    exponential backoff instead of crashing.
    """
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _build_headers(config: ClientConfig) -> dict[str, str]:
    headers: dict[str, str] = {
        "Authorization": config.auth_header,
        "User-Agent": _USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if config.org_id:
        headers["X-Org-Id"] = config.org_id
    return headers


def _raise_for_status(response: httpx.Response) -> None:
    """Map an unsuccessful HTTP response to a typed exception."""
    if response.is_success:
        return

    body: dict[str, Any] | None = None
    message = f"HTTP {response.status_code}"
    try:
        body = response.json()
        if isinstance(body, dict):
            message = body.get("message", message)
    except Exception:
        message = response.text or message

    exc_cls = _exception_for_status(response.status_code)

    if exc_cls is RateLimitError:
        retry_after = _parse_retry_after(response.headers.get("retry-after"))
        raise RateLimitError(
            message,
            status_code=response.status_code,
            body=body,
            retry_after=retry_after,
        )

    raise exc_cls(message, status_code=response.status_code, body=body)


def _should_retry(
    method: str, status_code: int, attempt: int, max_retries: int
) -> bool:
    if attempt >= max_retries:
        return False
    if status_code not in _RETRYABLE_STATUSES:
        return False
    # Only retry mutating requests on rate-limit (429), not on 5xx.
    return method in _RETRYABLE_METHODS or status_code == 429


def _should_retry_transport_error(
    method: str, exc: httpx.HTTPError, attempt: int, max_retries: int
) -> bool:
    """Decide whether a transport-level (network) error is safe to retry.

    Connection-phase errors mean the request never reached the server, so they
    are safe to retry for any method. Errors that surface after the request may
    already be in flight (read timeouts, protocol errors) are only retried for
    idempotent methods, so a POST is never silently re-sent.
    """
    if attempt >= max_retries:
        return False
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
        return True
    return method in _RETRYABLE_METHODS


def _backoff_delay(attempt: int, retry_after: float | None) -> float:
    if retry_after is not None:
        return retry_after
    return min(0.5 * (2**attempt), 8.0)


def _retry_after_for_status(response: httpx.Response) -> float | None:
    """Extract the ``Retry-After`` delay for a rate-limited response, if any."""
    if response.status_code == 429:
        return _parse_retry_after(response.headers.get("retry-after"))
    return None


class SyncTransport:
    """Synchronous HTTP transport with retry and error mapping."""

    def __init__(
        self,
        config: ClientConfig,
        *,
        http_transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/") + "/v1",
            headers=_build_headers(config),
            timeout=config.timeout,
            transport=http_transport,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a request and return the parsed JSON response body."""
        attempt = 0
        while True:
            try:
                response = self._client.request(method, path, json=json, params=params)
            except httpx.HTTPError as exc:
                if _should_retry_transport_error(
                    method, exc, attempt, self._config.max_retries
                ):
                    time.sleep(_backoff_delay(attempt, None))
                    attempt += 1
                    continue
                raise ConnectionError(str(exc)) from exc

            if _should_retry(
                method,
                response.status_code,
                attempt,
                self._config.max_retries,
            ):
                time.sleep(_backoff_delay(attempt, _retry_after_for_status(response)))
                attempt += 1
                continue

            _raise_for_status(response)

            if response.status_code == 204:
                return None
            return response.json()

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport with retry and error mapping."""

    def __init__(
        self,
        config: ClientConfig,
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/v1",
            headers=_build_headers(config),
            timeout=config.timeout,
            transport=http_transport,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a request and return the parsed JSON response body."""
        attempt = 0
        while True:
            try:
                response = await self._client.request(
                    method, path, json=json, params=params
                )
            except httpx.HTTPError as exc:
                if _should_retry_transport_error(
                    method, exc, attempt, self._config.max_retries
                ):
                    await asyncio.sleep(_backoff_delay(attempt, None))
                    attempt += 1
                    continue
                raise ConnectionError(str(exc)) from exc

            if _should_retry(
                method,
                response.status_code,
                attempt,
                self._config.max_retries,
            ):
                await asyncio.sleep(
                    _backoff_delay(attempt, _retry_after_for_status(response))
                )
                attempt += 1
                continue

            _raise_for_status(response)

            if response.status_code == 204:
                return None
            return response.json()

    async def close(self) -> None:
        await self._client.aclose()
