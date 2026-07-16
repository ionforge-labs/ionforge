"""HTTP transport layer wrapping httpx with retry, auth headers, and error mapping."""

from __future__ import annotations

import asyncio
import os
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
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


def _stream_headers() -> dict[str, str]:
    """Headers for the presigned-download client.

    Deliberately carries no ``Authorization`` (or ``X-Org-Id``): presigned URLs
    are cross-host storage links, and forwarding the API credential to a third
    party would leak it. Only the User-Agent is sent for observability.
    """
    return {"User-Agent": _USER_AGENT}


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
    are safe to retry for any method. A ``PoolTimeout`` means no connection was
    ever acquired from the pool, so the request likewise never left the client
    and is safe to retry regardless of method. Errors that surface after the
    request may already be in flight (read timeouts, protocol errors) are only
    retried for idempotent methods, so a POST is never silently re-sent.
    """
    if attempt >= max_retries:
        return False
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)):
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
        # Dedicated, unauthenticated client for cross-host presigned downloads.
        # It shares the configured timeout and the injected transport seam, but
        # carries no auth header and follows redirects (presigned links 307 to
        # storage), unlike a bare ``httpx.stream`` with its 5s default timeout.
        self._stream_client = httpx.Client(
            headers=_stream_headers(),
            timeout=config.timeout,
            follow_redirects=True,
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

    def stream_to_file(self, url: str, dest: Path) -> None:
        """Stream *url* to *dest* through the unauthenticated download client.

        A GET is idempotent, so the same retry policy as :meth:`request` applies:
        retryable statuses and connection errors back off and retry, and any
        terminal failure is mapped to the typed exception hierarchy. Redirects
        are followed and the configured timeout is honoured.

        Bytes land in a sibling ``.part`` temp file that is atomically renamed
        onto *dest* only once the stream completes, so a mid-stream failure never
        leaves a truncated result file behind. A retry reopens the temp in write
        mode, discarding any partial bytes from the prior attempt, and the temp
        is removed if the download ultimately fails.
        """
        tmp = dest.with_suffix(dest.suffix + ".part")
        attempt = 0
        try:
            while True:
                try:
                    with self._stream_client.stream("GET", url) as response:
                        if _should_retry(
                            "GET",
                            response.status_code,
                            attempt,
                            self._config.max_retries,
                        ):
                            time.sleep(
                                _backoff_delay(
                                    attempt, _retry_after_for_status(response)
                                )
                            )
                            attempt += 1
                            continue
                        if not response.is_success:
                            response.read()
                            _raise_for_status(response)
                        with open(tmp, "wb") as f:
                            for chunk in response.iter_bytes():
                                f.write(chunk)
                    os.replace(tmp, dest)
                    return
                except httpx.HTTPError as exc:
                    if _should_retry_transport_error(
                        "GET", exc, attempt, self._config.max_retries
                    ):
                        time.sleep(_backoff_delay(attempt, None))
                        attempt += 1
                        continue
                    raise ConnectionError(str(exc)) from exc
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def close(self) -> None:
        self._stream_client.close()
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
        # See ``SyncTransport``: an unauthenticated, redirect-following client
        # for cross-host presigned downloads, sharing the configured timeout and
        # injected transport seam.
        self._stream_client = httpx.AsyncClient(
            headers=_stream_headers(),
            timeout=config.timeout,
            follow_redirects=True,
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

    async def stream_to_file(self, url: str, dest: Path) -> None:
        """Stream *url* to *dest* through the unauthenticated download client.

        The async counterpart of :meth:`SyncTransport.stream_to_file`: same
        idempotent-GET retry policy, redirect following, configured timeout, and
        typed-exception mapping. Callers bound concurrency across many of these.

        As in the sync path, bytes land in a sibling ``.part`` temp file that is
        atomically renamed onto *dest* only once the stream completes, so a
        mid-stream failure never leaves a truncated result file behind. A retry
        reopens the temp in write mode, discarding any partial bytes from the
        prior attempt, and the temp is removed if the download ultimately fails.
        """
        tmp = dest.with_suffix(dest.suffix + ".part")
        attempt = 0
        try:
            while True:
                try:
                    async with self._stream_client.stream("GET", url) as response:
                        if _should_retry(
                            "GET",
                            response.status_code,
                            attempt,
                            self._config.max_retries,
                        ):
                            await asyncio.sleep(
                                _backoff_delay(
                                    attempt, _retry_after_for_status(response)
                                )
                            )
                            attempt += 1
                            continue
                        if not response.is_success:
                            await response.aread()
                            _raise_for_status(response)
                        with open(tmp, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)
                    os.replace(tmp, dest)
                    return
                except httpx.HTTPError as exc:
                    if _should_retry_transport_error(
                        "GET", exc, attempt, self._config.max_retries
                    ):
                        await asyncio.sleep(_backoff_delay(attempt, None))
                        attempt += 1
                        continue
                    raise ConnectionError(str(exc)) from exc
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    async def close(self) -> None:
        await self._stream_client.aclose()
        await self._client.aclose()
