"""Pagination tests: PageIterator / AsyncPageIterator across pages."""

from __future__ import annotations

import asyncio

import httpx

from .conftest import Router, make_async_client, make_client, make_project, page


def _paged_handler(total: int, page_size: int):
    """Return items sliced by the ``offset``/``limit`` query params."""
    items = [make_project(id=f"proj_{i}") for i in range(total)]

    def handler(req: httpx.Request) -> httpx.Response:
        offset = int(req.url.params.get("offset", "0"))
        limit = int(req.url.params.get("limit", str(page_size)))
        return httpx.Response(200, json=page(items[offset : offset + limit], total))

    return handler


def test_page_iterator_spans_multiple_pages() -> None:
    client = make_client(Router().add("GET", r"/v1/projects", _paged_handler(3, 2)))
    ids = [p.id for p in client.projects.list_autopaginate(page_size=2)]
    assert ids == ["proj_0", "proj_1", "proj_2"]


def test_page_iterator_single_full_page() -> None:
    client = make_client(Router().add("GET", r"/v1/projects", _paged_handler(2, 2)))
    ids = [p.id for p in client.projects.list_autopaginate(page_size=2)]
    assert ids == ["proj_0", "proj_1"]


def test_page_iterator_terminates_on_empty_page() -> None:
    router = Router().json("GET", r"/v1/projects", page([], total=0))
    client = make_client(router)
    assert list(client.projects.list_autopaginate(page_size=2)) == []


def _clamped_handler(total: int, server_max: int):
    """A server that clamps every page below the client's requested limit."""
    items = [make_project(id=f"proj_{i}") for i in range(total)]

    def handler(req: httpx.Request) -> httpx.Response:
        offset = int(req.url.params.get("offset", "0"))
        limit = int(req.url.params.get("limit", str(total)))
        window = min(limit, server_max)
        return httpx.Response(200, json=page(items[offset : offset + window], total))

    return handler


def test_page_iterator_handles_server_clamped_pages() -> None:
    # The client asks for 10 per page but the server never returns more than 2.
    # Advancing by the requested size would skip items, so all five must still
    # arrive when the iterator advances by the count actually returned.
    client = make_client(Router().add("GET", r"/v1/projects", _clamped_handler(5, 2)))
    ids = [p.id for p in client.projects.list_autopaginate(page_size=10)]
    assert ids == ["proj_0", "proj_1", "proj_2", "proj_3", "proj_4"]


def test_page_iterator_terminates_on_empty_page_despite_total() -> None:
    # A server that reports a positive total but returns no items must not spin
    # forever: an empty page means exhausted regardless of the reported total.
    router = Router().json("GET", r"/v1/projects", page([], total=99))
    client = make_client(router)
    assert list(client.projects.list_autopaginate(page_size=2)) == []


def test_async_page_iterator_spans_multiple_pages() -> None:
    async def go() -> list[str]:
        client = make_async_client(
            Router().add("GET", r"/v1/projects", _paged_handler(5, 2))
        )
        ids = [p.id async for p in client.projects.list_autopaginate(page_size=2)]
        await client.close()
        return ids

    assert asyncio.run(go()) == ["proj_0", "proj_1", "proj_2", "proj_3", "proj_4"]


def test_async_page_iterator_terminates_on_empty_page() -> None:
    async def go() -> list[str]:
        client = make_async_client(
            Router().json("GET", r"/v1/projects", page([], total=0))
        )
        ids = [p.id async for p in client.projects.list_autopaginate(page_size=2)]
        await client.close()
        return ids

    assert asyncio.run(go()) == []
