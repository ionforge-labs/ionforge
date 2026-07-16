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
