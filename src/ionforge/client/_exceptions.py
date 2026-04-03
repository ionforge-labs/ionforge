"""Typed exception hierarchy for IonForge API errors."""

from __future__ import annotations

from typing import Any


class APIError(Exception):
    """Base class for all IonForge API errors."""

    status_code: int
    message: str
    body: dict[str, Any] | None

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status={self.status_code}, message={self.message!r})"
        )


class AuthenticationError(APIError):
    """Raised on HTTP 401 — invalid or missing credentials."""


class PermissionDeniedError(APIError):
    """Raised on HTTP 403 — valid credentials but insufficient access."""


class NotFoundError(APIError):
    """Raised on HTTP 404 — resource does not exist."""


class BadRequestError(APIError):
    """Raised on HTTP 400 — malformed request or validation failure."""


class ConflictError(APIError):
    """Raised on HTTP 409 — resource conflict (e.g. deletion blocked by dependents)."""


class RateLimitError(APIError):
    """Raised on HTTP 429 — too many requests."""

    retry_after: float | None

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        body: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after = retry_after


class InternalServerError(APIError):
    """Raised on HTTP 5xx — server-side failure."""


class ConnectionError(APIError):
    """Raised on network-level failures (timeout, DNS, etc.)."""


_STATUS_TO_EXCEPTION: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def _exception_for_status(status_code: int) -> type[APIError]:
    """Return the appropriate exception class for an HTTP status code."""
    if status_code in _STATUS_TO_EXCEPTION:
        return _STATUS_TO_EXCEPTION[status_code]
    if status_code >= 500:
        return InternalServerError
    return APIError
