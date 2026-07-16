"""Base classes for sync and async resource namespaces."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel

from .._transport import AsyncTransport, SyncTransport


def _wire_key(field: Any, name: str) -> str:
    """Return the key a field serialises to under ``by_alias=True``."""
    return field.serialization_alias or field.alias or name


def _inject_constants(model: BaseModel, dumped: dict[str, Any]) -> None:
    """Insert single-value ``Literal`` wire constants missing from *dumped*.

    A field typed as a one-value ``Literal`` (for example a schema-version
    discriminator ``Literal[1]`` or a ``units`` tag ``Literal["m"]``) carries
    exactly one legal value and must always appear on the wire. When a model is
    built from its Python-side default rather than an explicit argument, that
    field never lands in ``model_fields_set``, so an ``exclude_unset`` dump
    drops it. This walks the model (read-only) alongside its already-dumped dict
    and writes each such constant back in under its wire key where absent, so
    the sparse-serialisation gain applies only to genuinely optional fields.

    The model itself is never mutated: constants are injected into *dumped*, the
    freshly produced plain dict, so the caller's model is left bit-identical and
    no deep copy of the (possibly huge) geometry tree is taken. Recursion
    descends only into children that survived the dump - a nested model dropped
    as unset or ``None`` is absent from both the wire and this walk.
    """
    for name, field in type(model).model_fields.items():
        key = _wire_key(field, name)
        annotation = field.annotation
        args = get_args(annotation)
        if get_origin(annotation) is Literal and len(args) == 1 and key not in dumped:
            const = args[0]
            dumped[key] = const.value if isinstance(const, Enum) else const

        value = getattr(model, name, None)
        child = dumped.get(key)
        if isinstance(value, BaseModel) and isinstance(child, dict):
            _inject_constants(value, child)
        elif isinstance(value, (list, tuple)) and isinstance(child, list):
            for item, item_dumped in zip(value, child, strict=False):
                if isinstance(item, BaseModel) and isinstance(item_dumped, dict):
                    _inject_constants(item, item_dumped)
        elif isinstance(value, dict) and isinstance(child, dict):
            for item_key, item in value.items():
                item_dumped = child.get(item_key, child.get(str(item_key)))
                if isinstance(item, BaseModel) and isinstance(item_dumped, dict):
                    _inject_constants(item, item_dumped)


def _serialize(obj: Any) -> Any:
    """Serialize a value for JSON transport, respecting camelCase aliases.

    ``exclude_unset=True`` keeps sparse models sparse on the wire: only the
    fields the caller actually set are sent, so run-level overrides carry just
    the changed values instead of re-inflating to the full default object and
    clobbering stored parameters. Single-value ``Literal`` wire constants are
    injected back into the dumped body afterwards so they are never dropped as
    "unset".
    """
    if isinstance(obj, BaseModel):
        # Dump first, then inject constants into the resulting plain dict. The
        # model is only ever read, so a shared instance can be serialised from
        # many threads at once without racing on its fields-set, and no deep
        # copy of the (possibly huge) tree is taken.
        dumped = obj.model_dump(
            by_alias=True, exclude_none=True, exclude_unset=True, mode="json"
        )
        if isinstance(dumped, dict):
            _inject_constants(obj, dumped)
        return dumped
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
