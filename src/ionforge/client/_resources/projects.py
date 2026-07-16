"""Projects resource."""

from __future__ import annotations

from collections.abc import Iterator

from ionforge._types._generated import (
    CreateProjectRequest,
    Project,
    ProjectWithCounts,
    UpdateProjectRequest,
)

from .._models.pagination import Page
from .._pagination import AsyncPageIterator, PageIterator
from ._base import BaseAsyncResource, BaseSyncResource


def _list_params(
    *,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if search is not None:
        params["search"] = search
    return params


class Projects(BaseSyncResource):
    """Synchronous projects resource."""

    def create(
        self,
        *,
        name: str,
        description: str | None = None,
    ) -> Project:
        """Create a new project."""
        data = self._post(
            "/projects",
            body=CreateProjectRequest(name=name, description=description),
        )
        return Project.model_validate(data)

    def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
    ) -> Page[Project]:
        """List projects (paginated)."""
        data = self._get(
            "/projects",
            params=_list_params(limit=limit, offset=offset, search=search),
        )
        return Page[Project].model_validate(data)

    def list_autopaginate(
        self,
        *,
        search: str | None = None,
        page_size: int = 25,
    ) -> Iterator[Project]:
        """Iterate over all projects, fetching pages automatically."""
        return PageIterator(
            fetch=lambda offset: self.list(
                limit=page_size, offset=offset, search=search
            ),
            page_size=page_size,
        )

    def get(self, id: str) -> ProjectWithCounts:
        """Get a project by ID."""
        data = self._get(f"/projects/{id}")
        return ProjectWithCounts.model_validate(data)

    def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Project:
        """Update a project."""
        data = self._put(
            f"/projects/{id}",
            body=UpdateProjectRequest(name=name, description=description),
        )
        return Project.model_validate(data)

    def delete(self, id: str) -> None:
        """Delete a project."""
        self._delete(f"/projects/{id}")


class AsyncProjects(BaseAsyncResource):
    """Asynchronous projects resource."""

    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
    ) -> Project:
        """Create a new project."""
        data = await self._post(
            "/projects",
            body=CreateProjectRequest(name=name, description=description),
        )
        return Project.model_validate(data)

    async def list(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
    ) -> Page[Project]:
        """List projects (paginated)."""
        data = await self._get(
            "/projects",
            params=_list_params(limit=limit, offset=offset, search=search),
        )
        return Page[Project].model_validate(data)

    def list_autopaginate(
        self,
        *,
        search: str | None = None,
        page_size: int = 25,
    ) -> AsyncPageIterator[Project]:
        """Iterate over all projects, fetching pages automatically."""
        return AsyncPageIterator(
            fetch=lambda offset: self.list(
                limit=page_size, offset=offset, search=search
            ),
            page_size=page_size,
        )

    async def get(self, id: str) -> ProjectWithCounts:
        """Get a project by ID."""
        data = await self._get(f"/projects/{id}")
        return ProjectWithCounts.model_validate(data)

    async def update(
        self,
        id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Project:
        """Update a project."""
        data = await self._put(
            f"/projects/{id}",
            body=UpdateProjectRequest(name=name, description=description),
        )
        return Project.model_validate(data)

    async def delete(self, id: str) -> None:
        """Delete a project."""
        await self._delete(f"/projects/{id}")
