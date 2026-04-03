"""HTTP transport layer wrapping httpx with retry, auth headers, and error mapping."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ._config import ClientConfig
from ._exceptions import (
    ConnectionError,
    RateLimitError,
    _exception_for_status,
)

_VERSION = "0.1.0"
_USER_AGENT = f"ionforge-python/{_VERSION}"

# Status codes that trigger automatic retry.
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# HTTP methods considered safe to retry (idempotent).
_RETRYABLE_METHODS = {"GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


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
        retry_after_raw = response.headers.get("retry-after")
        retry_after = float(retry_after_raw) if retry_after_raw else None
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


def _backoff_delay(attempt: int, retry_after: float | None) -> float:
    if retry_after is not None:
        return retry_after
    return min(0.5 * (2**attempt), 8.0)


class SyncTransport:
    """Synchronous HTTP transport with retry and error mapping."""

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/") + "/v1",
            headers=_build_headers(config),
            timeout=config.timeout,
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
                if attempt < self._config.max_retries:
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
                retry_after = None
                if response.status_code == 429:
                    raw = response.headers.get("retry-after")
                    retry_after = float(raw) if raw else None
                time.sleep(_backoff_delay(attempt, retry_after))
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

    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/v1",
            headers=_build_headers(config),
            timeout=config.timeout,
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
        import asyncio

        attempt = 0
        while True:
            try:
                response = await self._client.request(
                    method, path, json=json, params=params
                )
            except httpx.HTTPError as exc:
                if attempt < self._config.max_retries:
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
                retry_after = None
                if response.status_code == 429:
                    raw = response.headers.get("retry-after")
                    retry_after = float(raw) if raw else None
                await asyncio.sleep(_backoff_delay(attempt, retry_after))
                attempt += 1
                continue

            _raise_for_status(response)

            if response.status_code == 204:
                return None
            return response.json()

    async def close(self) -> None:
        await self._client.aclose()
