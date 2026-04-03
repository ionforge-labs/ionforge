"""Generic paginated response wrapper."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A single page of results from a list endpoint."""

    items: list[T]
    total: int

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):  # type: ignore[override]
        return iter(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]

    def __repr__(self) -> str:
        return f"Page(items=[...{len(self.items)} items], total={self.total})"
