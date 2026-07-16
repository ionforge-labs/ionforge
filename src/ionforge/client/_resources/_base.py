"""Base classes for sync and async resource namespaces."""

from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel

from .._transport import AsyncTransport, SyncTransport


def _pin_constant_fields(model: BaseModel) -> None:
    """Mark single-value ``Literal`` wire constants as set across the model tree.

    A field typed as a one-value ``Literal`` (for example a schema-version
    discriminator ``Literal[1]``) carries exactly one legal value and must
    always appear on the wire. When a model is built from its Python-side
    default rather than an explicit argument, that field never lands in
    ``model_fields_set``, so an ``exclude_unset`` dump would drop it. Pin such
    constants (recursing into nested models) so the sparse-serialisation gain
    applies only to genuinely optional fields.
    """
    for name, field in type(model).model_fields.items():
        annotation = field.annotation
        if get_origin(annotation) is Literal and len(get_args(annotation)) == 1:
            model.__pydantic_fields_set__.add(name)
        value = getattr(model, name, None)
        if isinstance(value, BaseModel):
            _pin_constant_fields(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, BaseModel):
                    _pin_constant_fields(item)
        elif isinstance(value, dict):
            for item in value.values():
                if isinstance(item, BaseModel):
                    _pin_constant_fields(item)


def _serialize(obj: Any) -> Any:
    """Serialize a value for JSON transport, respecting camelCase aliases.

    ``exclude_unset=True`` keeps sparse models sparse on the wire: only the
    fields the caller actually set are sent, so run-level overrides carry just
    the changed values instead of re-inflating to the full default object and
    clobbering stored parameters. Single-value ``Literal`` wire constants are
    pinned first so they are never dropped as "unset".
    """
    if isinstance(obj, BaseModel):
        # Operate on a copy so pinning never mutates the caller's model.
        obj = obj.model_copy(deep=True)
        _pin_constant_fields(obj)
        return obj.model_dump(
            by_alias=True, exclude_none=True, exclude_unset=True, mode="json"
        )
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
