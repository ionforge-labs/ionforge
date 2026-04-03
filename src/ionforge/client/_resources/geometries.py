"""Geometries resource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .._generated import (
    CreateGeometryRequest,
    GeometryListItem,
    GeometryMeta,
    GetGeometryResponse,
    SerializedGeometry,
    UpdateGeometryRequest,
)
from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from ._base import BaseAsyncResource, BaseSyncResource


def _list_params(
    *,
    project_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if project_id is not None:
        params["projectId"] = project_id
    if search is not None:
        params["search"] = search
    return params


class Geometries(BaseSyncResource):
    """Synchronous geometries resource."""

    def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        geometry_data: SerializedGeometry | dict[str, Any],
    ) -> GeometryMeta:
        """Create a geometry."""
        if isinstance(geometry_data, dict):
            geometry_data = SerializedGeometry.model_validate(geometry_data)
        data = self._post(
            "/geometries",
            body=CreateGeometryRequest(
                project_id=project_id,
                name=name,
                description=description,
                geometry_data=geometry_data,
            ),
        )
        return GeometryMeta.model_validate(data)

    def list(
        self,
        *,
        project_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
    ) -> Page[GeometryListItem]:
        """List geometries (metadata only)."""
        data = self._get(
            "/geometries",
            params=_list_params(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
            ),
        )
        return Page[GeometryListItem].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        search: str | None = None,
        page_size: int = 25,
    ) -> Iterator[GeometryListItem]:
        """Iterate over all geometries, fetching pages automatically."""
        return PageIterator(
            fetch=lambda offset: self.list(
                project_id=project_id,
                limit=page_size,
                offset=offset,
                search=search,
            ),
            page_size=page_size,
        )

    def get(self, id: str) -> GetGeometryResponse:
        """Get a geometry including its full mesh data."""
        data = self._get(f"/geometries/{id}")
        return GetGeometryResponse.model_validate(data)

    def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        geometry_data: SerializedGeometry | dict[str, Any] | None = None,
    ) -> GeometryMeta:
        """Update a geometry."""
        if isinstance(geometry_data, dict):
            geometry_data = SerializedGeometry.model_validate(geometry_data)
        data = self._put(
            f"/geometries/{id}",
            body=UpdateGeometryRequest(
                name=name,
                description=description,
                geometry_data=geometry_data,
            ),
        )
        return GeometryMeta.model_validate(data)

    def delete(self, id: str) -> None:
        """Delete a geometry."""
        self._delete(f"/geometries/{id}")


class AsyncGeometries(BaseAsyncResource):
    """Asynchronous geometries resource."""

    async def create(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        geometry_data: SerializedGeometry | dict[str, Any],
    ) -> GeometryMeta:
        """Create a geometry."""
        if isinstance(geometry_data, dict):
            geometry_data = SerializedGeometry.model_validate(geometry_data)
        data = await self._post(
            "/geometries",
            body=CreateGeometryRequest(
                project_id=project_id,
                name=name,
                description=description,
                geometry_data=geometry_data,
            ),
        )
        return GeometryMeta.model_validate(data)

    async def list(
        self,
        *,
        project_id: str | None = None,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
    ) -> Page[GeometryListItem]:
        """List geometries (metadata only)."""
        data = await self._get(
            "/geometries",
            params=_list_params(
                project_id=project_id,
                limit=limit,
                offset=offset,
                search=search,
            ),
        )
        return Page[GeometryListItem].model_validate(data)

    def list_autopaginate(
        self,
        *,
        project_id: str | None = None,
        search: str | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[GeometryListItem]:
        """Iterate over all geometries, fetching pages automatically."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                project_id=project_id,
                limit=page_size,
                offset=offset,
                search=search,
            ),
            page_size=page_size,
        )

    async def get(self, id: str) -> GetGeometryResponse:
        """Get a geometry including its full mesh data."""
        data = await self._get(f"/geometries/{id}")
        return GetGeometryResponse.model_validate(data)

    async def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        geometry_data: SerializedGeometry | dict[str, Any] | None = None,
    ) -> GeometryMeta:
        """Update a geometry."""
        if isinstance(geometry_data, dict):
            geometry_data = SerializedGeometry.model_validate(geometry_data)
        data = await self._put(
            f"/geometries/{id}",
            body=UpdateGeometryRequest(
                name=name,
                description=description,
                geometry_data=geometry_data,
            ),
        )
        return GeometryMeta.model_validate(data)

    async def delete(self, id: str) -> None:
        """Delete a geometry."""
        await self._delete(f"/geometries/{id}")
