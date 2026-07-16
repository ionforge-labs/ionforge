"""Shared fixtures and helpers for the API client test suite.

Every test drives the real client stack (config -> transport -> resources)
against an ``httpx.MockTransport`` injected through the private
``_http_transport`` hook, so nothing ever touches the network.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import httpx
import pytest

from ionforge.client import AsyncIonForge, IonForge
from ionforge.geometry import Cylinder, Geometry

TS = "2026-01-01T00:00:00Z"


@pytest.fixture
def einzel_geometry() -> Geometry:
    """A minimal single-tube geometry builder for upload tests."""
    geo = Geometry(bounding_box=(0.05, 0.05, 0.10))
    geo.add(Cylinder(r=0.01, length=0.04, voltage=0.0, name="tube"))
    return geo


@pytest.fixture
def einzel_serialized(einzel_geometry: Geometry):
    """The serialized form of :func:`einzel_geometry`."""
    return einzel_geometry.to_serialized_geometry()


Handler = Callable[[httpx.Request], httpx.Response]


class Router:
    """Minimal method+path router that records every request it receives."""

    def __init__(self) -> None:
        self._routes: list[tuple[str, re.Pattern[str], Handler]] = []
        self.requests: list[httpx.Request] = []

    def add(self, method: str, pattern: str, handler: Handler) -> Router:
        """Register a handler for requests matching *method* and path *pattern*."""
        self._routes.append((method, re.compile(pattern), handler))
        return self

    def json(
        self, method: str, pattern: str, body: object, status: int = 200
    ) -> Router:
        """Register a static JSON response."""
        return self.add(method, pattern, lambda _req: httpx.Response(status, json=body))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for method, pattern, handler in self._routes:
            if request.method == method and pattern.fullmatch(request.url.path):
                return handler(request)
        return httpx.Response(
            599,
            json={"message": f"unrouted {request.method} {request.url.path}"},
        )

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


def make_client(handler: Handler, **kwargs: object) -> IonForge:
    """Build a sync client whose transport is backed by *handler*."""
    kwargs.setdefault("api_key", "ifk_test")
    kwargs.setdefault("org_id", "org_123")
    return IonForge(_http_transport=httpx.MockTransport(handler), **kwargs)  # type: ignore[arg-type]


def make_async_client(handler: Handler, **kwargs: object) -> AsyncIonForge:
    """Build an async client whose transport is backed by *handler*."""
    kwargs.setdefault("api_key", "ifk_test")
    kwargs.setdefault("org_id", "org_123")
    return AsyncIonForge(_http_transport=httpx.MockTransport(handler), **kwargs)  # type: ignore[arg-type]


# --- Response-body factories (camelCase wire shapes) -----------------------


def make_project(**over: object) -> dict[str, object]:
    body = {
        "id": "proj_1",
        "orgId": "org_1",
        "createdBy": "usr_1",
        "name": "Project",
        "description": None,
        "createdAt": TS,
        "updatedAt": TS,
    }
    body.update(over)
    return body


def make_project_with_counts(**over: object) -> dict[str, object]:
    body = make_project()
    body.update({"modelCount": 0, "geometryCount": 0})
    body.update(over)
    return body


def make_model_with_counts(**over: object) -> dict[str, object]:
    body = make_model()
    body.update({"runCount": 0, "latestRunStatus": None})
    body.update(over)
    return body


def make_geometry_meta(**over: object) -> dict[str, object]:
    body = {
        "id": "geo_1",
        "orgId": "org_1",
        "createdBy": "usr_1",
        "projectId": "proj_1",
        "name": "Geometry",
        "description": None,
        "sizeBytes": 2048.0,
        "vertexCount": 10,
        "faceCount": 8,
        "groupCount": 2,
        "thumbnailUrl": None,
        "createdAt": TS,
        "updatedAt": TS,
    }
    body.update(over)
    return body


def make_model(**over: object) -> dict[str, object]:
    body = {
        "id": "mdl_1",
        "orgId": "org_1",
        "userId": "usr_1",
        "projectId": "proj_1",
        "name": "Model",
        "description": None,
        "simulatorType": "ion_optics",
        "geometryId": "geo_1",
        "params": None,
        "isTemplate": False,
        "editorLockHolderId": None,
        "editorLockExpiresAt": None,
        "displayImageUrl": None,
        "objectiveMetric": None,
        "objectiveDirection": None,
        "createdAt": TS,
        "updatedAt": TS,
    }
    body.update(over)
    return body


def make_run(**over: object) -> dict[str, object]:
    body = {
        "id": "run_1",
        "orgId": "org_1",
        "userId": "usr_1",
        "modelId": "mdl_1",
        "name": "Run",
        "status": "queued",
        "simulatorType": "ion_optics",
        "geometryId": "geo_1",
        "params": None,
        "sweepId": None,
        "sweepPoint": None,
        "errorMessage": None,
        "errorMessageRaw": None,
        "errorCode": None,
        "traceId": None,
        "createdAt": TS,
        "startedAt": None,
        "completedAt": None,
    }
    body.update(over)
    return body


def make_sweep(**over: object) -> dict[str, object]:
    body = {
        "id": "swp_1",
        "orgId": "org_1",
        "userId": "usr_1",
        "modelId": "mdl_1",
        "name": "Sweep",
        "status": "queued",
        "strategy": "grid",
        "parameterSpace": None,
        "axes": None,
        "totalPoints": 4,
        "completedPoints": 0,
        "objectiveMetric": None,
        "objectiveDirection": None,
        "bestRunId": None,
        "bestSettledAt": None,
        "parentSweepId": None,
        "createdAt": TS,
        "startedAt": None,
        "completedAt": None,
    }
    body.update(over)
    return body


def make_result(**over: object) -> dict[str, object]:
    body = {
        "id": "res_1",
        "runId": "run_1",
        "summary": None,
        "solverMeta": None,
        "fileSize": 1234.0,
        "createdAt": TS,
    }
    body.update(over)
    return body


def page(items: list[object], total: int | None = None) -> dict[str, object]:
    return {"items": items, "total": total if total is not None else len(items)}
