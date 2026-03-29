"""Pydantic v2 models for the SerializedGeometry format.

These are the canonical Python definition of the geometry schema shared
between the TypeScript frontend (via generated Zod) and the Python
simulator (via the converter module).

Design constraints
------------------
- Zero scipy imports (Pyodide-safe).
- numpy allowed but not required for the models themselves.
- Field names are snake_case in Python, camelCase when serialised to JSON
  (matching the TypeScript ``SerializedGeometry`` interface).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class _CamelModel(BaseModel):
    """Base with camelCase JSON aliases and sensible defaults."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )


# ------------------------------------------------------------------
# Primitives
# ------------------------------------------------------------------

Vec3 = tuple[float, float, float]


class Vertex(_CamelModel):
    id: str
    position: Vec3  # metres


class Edge(_CamelModel):
    id: str
    v0: str  # vertex ID
    v1: str  # vertex ID
    # Defaults to [] so standalone edges (no adjacent faces) can omit faceIds.
    # The TypeScript Zod schema requires faceIds but the frontend always
    # serializes it (even when empty), so this is backward-compatible.
    face_ids: list[str] = Field(default_factory=list)


class Face(_CamelModel):
    id: str
    vertex_ids: list[str] = Field(min_length=3)
    edge_ids: list[str]


class BoundingBox(_CamelModel):
    size: Vec3  # metres
    voltage: float  # boundary condition (V), typically 0


class Group(_CamelModel):
    id: str
    name: str
    color: str  # hex colour
    voltage: float | None  # None = unassigned
    face_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)


# ------------------------------------------------------------------
# Root model
# ------------------------------------------------------------------


class SerializedGeometry(_CamelModel):
    version: Literal[1] = 1
    units: Literal["m"] = "m"
    vertices: list[Vertex]
    edges: list[Edge]
    faces: list[Face]
    bounding_box: BoundingBox
    groups: list[Group]
    group_order: list[str]

    def validate_consistency(self) -> list[str]:
        """Check cross-field invariants that Pydantic can't express.

        Returns a list of human-readable error strings.
        Empty list = geometry is consistent.
        """
        errors: list[str] = []

        vertex_ids = {v.id for v in self.vertices}
        edge_ids = {e.id for e in self.edges}
        face_ids = {f.id for f in self.faces}
        group_ids = {g.id for g in self.groups}

        # Edges reference valid vertices
        for edge in self.edges:
            if edge.v0 not in vertex_ids:
                errors.append(f"edge '{edge.id}' references unknown vertex '{edge.v0}'")
            if edge.v1 not in vertex_ids:
                errors.append(f"edge '{edge.id}' references unknown vertex '{edge.v1}'")
            for fid in edge.face_ids:
                if fid not in face_ids:
                    errors.append(f"edge '{edge.id}' references unknown face '{fid}'")

        # Faces reference valid vertices and edges
        for face in self.faces:
            for vid in face.vertex_ids:
                if vid not in vertex_ids:
                    errors.append(f"face '{face.id}' references unknown vertex '{vid}'")
            for eid in face.edge_ids:
                if eid not in edge_ids:
                    errors.append(f"face '{face.id}' references unknown edge '{eid}'")

        # Groups reference valid faces and edges
        for group in self.groups:
            for fid in group.face_ids:
                if fid not in face_ids:
                    errors.append(
                        f"group '{group.name}' references unknown face '{fid}'"
                    )
            for eid in group.edge_ids:
                if eid not in edge_ids:
                    errors.append(
                        f"group '{group.name}' references unknown edge '{eid}'"
                    )

        # Group order references valid groups
        for gid in self.group_order:
            if gid not in group_ids:
                errors.append(f"groupOrder references unknown group '{gid}'")

        # Every face belongs to at most one group
        seen_faces: dict[str, str] = {}
        for group in self.groups:
            for fid in group.face_ids:
                if fid in seen_faces:
                    errors.append(
                        f"face '{fid}' belongs to both group "
                        f"'{seen_faces[fid]}' and '{group.name}'"
                    )
                else:
                    seen_faces[fid] = group.name

        return errors

    def all_groups_have_voltage(self) -> list[str]:
        """Return names of groups with ``voltage is None``."""
        return [g.name for g in self.groups if g.voltage is None]
