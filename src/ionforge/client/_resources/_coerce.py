"""Helpers for normalising ergonomic argument unions at the request boundary.

Public resource methods accept forgiving unions - an enum *or* its string form,
a typed model *or* a plain ``dict`` - so callers do not have to import the
generated enum/model classes. The generated request models, however, declare the
strict types. These helpers coerce the ergonomic value into the strict type once,
at the point where the request model is constructed, keeping the public
signatures friendly and the request construction type-correct.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeVar, overload

from pydantic import BaseModel, TypeAdapter

_EnumT = TypeVar("_EnumT", bound=StrEnum)
_ModelT = TypeVar("_ModelT", bound=BaseModel)
_ItemT = TypeVar("_ItemT")


def to_enum(enum_cls: type[_EnumT], value: _EnumT | str | None) -> _EnumT | None:
    """Coerce an enum member or its string value into *enum_cls* (``None`` passes)."""
    if value is None:
        return None
    return enum_cls(value)


@overload
def to_model(model_cls: type[_ModelT], value: None) -> None: ...


@overload
def to_model(model_cls: type[_ModelT], value: object) -> _ModelT: ...


def to_model(model_cls: type[_ModelT], value: object) -> _ModelT | None:
    """Coerce a model instance or a plain ``dict`` into *model_cls* (``None`` passes).

    ``value`` is typed as ``object`` so the model type is inferred solely from
    *model_cls*; callers pass a ``model_cls | dict | None`` ergonomic union. The
    overloads narrow the result to non-``None`` for a non-``None`` argument, so a
    required request field stays type-correct without an extra guard.
    """
    if value is None:
        return None
    if isinstance(value, model_cls):
        return value
    return model_cls.model_validate(value)


def to_list(adapter: TypeAdapter[list[_ItemT]], value: list[Any]) -> list[_ItemT]:
    """Validate a list of mixed model/``dict`` items against *adapter*'s item union."""
    return adapter.validate_python(value)
