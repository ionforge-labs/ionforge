"""Async parity spot-checks: get / list / create through the async client."""

from __future__ import annotations

import asyncio
import json

import httpx

from .conftest import (
    Router,
    make_async_client,
    make_model,
    make_project,
    make_project_with_counts,
    page,
)


def test_async_create_posts_camelcase_body() -> None:
    async def go() -> httpx.Request:
        router = Router().json("POST", r"/v1/projects", make_project())
        client = make_async_client(router)
        await client.projects.create(name="Async project")
        await client.close()
        return router.last

    req = asyncio.run(go())
    assert req.method == "POST"
    assert json.loads(req.content) == {"name": "Async project"}


def test_async_get_hits_id_path() -> None:
    async def go() -> str:
        router = Router().json(
            "GET", r"/v1/projects/proj_5", make_project_with_counts(id="proj_5")
        )
        client = make_async_client(router)
        proj = await client.projects.get("proj_5")
        await client.close()
        return proj.id

    assert asyncio.run(go()) == "proj_5"


def test_async_list_returns_page() -> None:
    async def go() -> int:
        router = Router().json(
            "GET", r"/v1/models", page([make_model(), make_model(id="mdl_2")])
        )
        client = make_async_client(router)
        result = await client.models.list()
        await client.close()
        return result.total

    assert asyncio.run(go()) == 2


def test_async_auth_header_present() -> None:
    async def go() -> httpx.Request:
        router = Router().json("POST", r"/v1/projects", make_project())
        client = make_async_client(router, api_key="ifk_async", org_id="org_9")
        await client.projects.create(name="P")
        await client.close()
        return router.last

    req = asyncio.run(go())
    assert req.headers["Authorization"] == "Bearer ifk_async"
    assert req.headers["X-Org-Id"] == "org_9"
