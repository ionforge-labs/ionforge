"""Client configuration and environment variable resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass

PRODUCTION_BASE_URL = "https://api.ionforge.io"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3


@dataclass(frozen=True)
class ClientConfig:
    """Resolved configuration for an IonForge API client."""

    api_key: str | None
    session_token: str | None
    org_id: str | None
    base_url: str
    timeout: float
    max_retries: int

    @property
    def auth_header(self) -> str:
        """Return the Authorization header value."""
        credential = self.api_key or self.session_token
        if credential is None:
            raise ValueError(
                "No credentials provided. Pass api_key= to IonForge() "
                "or set the IONFORGE_API_KEY environment variable."
            )
        return f"Bearer {credential}"


def resolve_config(
    *,
    api_key: str | None = None,
    session_token: str | None = None,
    org_id: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> ClientConfig:
    """Build a ClientConfig from explicit arguments and env vars."""
    return ClientConfig(
        api_key=api_key or os.environ.get("IONFORGE_API_KEY"),
        session_token=session_token,
        org_id=org_id or os.environ.get("IONFORGE_ORG_ID"),
        base_url=(
            base_url or os.environ.get("IONFORGE_BASE_URL") or PRODUCTION_BASE_URL
        ),
        timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
        max_retries=(max_retries if max_retries is not None else DEFAULT_MAX_RETRIES),
    )
