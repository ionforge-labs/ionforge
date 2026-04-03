"""Base classes for sync and async resource namespaces."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .._transport import AsyncTransport, SyncTransport


def _serialize(obj: Any) -> Any:
    """Serialize a value for JSON transport, respecting camelCase aliases."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(by_alias=True, exclude_none=True)
    return obj


class BaseSyncResource:
    """Base for synchronous resource namespaces."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self._transport.request("GET", path, params=params)

    def _post(self, path: str, *, body: Any = None) -> Any:
        return self._transport.request("POST", path, json=_serialize(body))

    def _put(self, path: str, *, body: Any = None) -> Any:
        return self._transport.request("PUT", path, json=_serialize(body))

    def _delete(self, path: str) -> Any:
        return self._transport.request("DELETE", path)


class BaseAsyncResource:
    """Base for asynchronous resource namespaces."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._transport.request("GET", path, params=params)

    async def _post(self, path: str, *, body: Any = None) -> Any:
        return await self._transport.request("POST", path, json=_serialize(body))

    async def _put(self, path: str, *, body: Any = None) -> Any:
        return await self._transport.request("PUT", path, json=_serialize(body))

    async def _delete(self, path: str) -> Any:
        return await self._transport.request("DELETE", path)
