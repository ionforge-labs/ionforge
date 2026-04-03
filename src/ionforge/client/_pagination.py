"""Auto-pagination iterators for list endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Generic, TypeVar

from ._models.pagination import Page

T = TypeVar("T")


class PageIterator(Generic[T], Iterator[T]):
    """Lazily fetches pages and yields individual items (sync)."""

    def __init__(
        self,
        fetch: Callable[[int], Page[T]],
        page_size: int,
    ) -> None:
        self._fetch = fetch
        self._page_size = page_size
        self._buffer: list[T] = []
        self._offset = 0
        self._total: int | None = None
        self._exhausted = False

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        if self._buffer:
            return self._buffer.pop(0)

        if self._exhausted:
            raise StopIteration

        page = self._fetch(self._offset)
        self._total = page.total
        self._offset += self._page_size

        if not page.items or self._offset >= page.total:
            self._exhausted = True

        if not page.items:
            raise StopIteration

        self._buffer = list(page.items[1:])
        return page.items[0]


class AsyncPageIterator(Generic[T], AsyncIterator[T]):
    """Lazily fetches pages and yields individual items (async)."""

    def __init__(
        self,
        fetch: Callable[[int], Awaitable[Page[T]]],
        page_size: int,
    ) -> None:
        self._fetch = fetch
        self._page_size = page_size
        self._buffer: list[T] = []
        self._offset = 0
        self._total: int | None = None
        self._exhausted = False

    def __aiter__(self) -> AsyncPageIterator[T]:
        return self

    async def __anext__(self) -> T:
        if self._buffer:
            return self._buffer.pop(0)

        if self._exhausted:
            raise StopAsyncIteration

        page = await self._fetch(self._offset)
        self._total = page.total
        self._offset += self._page_size

        if not page.items or self._offset >= page.total:
            self._exhausted = True

        if not page.items:
            raise StopAsyncIteration

        self._buffer = list(page.items[1:])
        return page.items[0]
