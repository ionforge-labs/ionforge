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
        self._cursor = 0
        self._offset = 0
        self._exhausted = False

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        while self._cursor >= len(self._buffer):
            if self._exhausted:
                raise StopIteration
            self._fetch_next_page()

        item = self._buffer[self._cursor]
        self._cursor += 1
        return item

    def _fetch_next_page(self) -> None:
        page = self._fetch(self._offset)
        # Advance by the number of items actually returned: a server is free to
        # clamp the page below the requested size, so trusting page_size here
        # would skip or repeat items. An empty page means exhaustion, whatever
        # the reported total claims.
        self._offset += len(page.items)
        if not page.items:
            self._exhausted = True
            return
        if self._offset >= page.total:
            self._exhausted = True
        self._buffer = list(page.items)
        self._cursor = 0


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
        self._cursor = 0
        self._offset = 0
        self._exhausted = False

    def __aiter__(self) -> AsyncPageIterator[T]:
        return self

    async def __anext__(self) -> T:
        while self._cursor >= len(self._buffer):
            if self._exhausted:
                raise StopAsyncIteration
            await self._fetch_next_page()

        item = self._buffer[self._cursor]
        self._cursor += 1
        return item

    async def _fetch_next_page(self) -> None:
        page = await self._fetch(self._offset)
        self._offset += len(page.items)
        if not page.items:
            self._exhausted = True
            return
        if self._offset >= page.total:
            self._exhausted = True
        self._buffer = list(page.items)
        self._cursor = 0
