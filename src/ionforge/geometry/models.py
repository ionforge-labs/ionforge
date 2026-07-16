"""Geometry models - overlay on generated types with validation methods.

The generated Pydantic models come from the OpenAPI spec via
``datamodel-code-generator``. This module re-exports them and adds
domain-specific validation that codegen can't produce.

Design constraints
------------------
- Zero scipy imports (Pyodide-safe).
- Field names are snake_case in Python, camelCase when serialised to JSON.
"""

from __future__ import annotations

from typing import Literal

from ionforge._types._generated import (
    BoundingBox,
    Edge,
    Face,
    Group,
    Symmetry,
)
from ionforge._types._generated import (
    SerializedGeometry as _GeneratedSerializedGeometry,
)
from ionforge._types._generated import (
    Vertice as Vertex,
)

Vec3 = tuple[float, float, float]


def _is_numeric_triple(values: object) -> bool:
    """True if *values* is a sequence of exactly 3 real numbers.

    Booleans are rejected even though ``bool`` subclasses ``int``: a coordinate
    of ``True`` is a data error, not a valid position component.
    """
    if not isinstance(values, list) or len(values) != 3:
        return False
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)


__all__ = [
    "BoundingBox",
    "Edge",
    "Face",
    "Group",
    "SerializedGeometry",
    "Symmetry",
    "Vec3",
    "Vertex",
]


class SerializedGeometry(_GeneratedSerializedGeometry):
    """Serialised geometry with cross-field validation."""

    version: Literal[1] = 1
    units: Literal["m"] = "m"

    def validate_consistency(self) -> list[str]:
        """Check cross-field invariants that Pydantic can't express.

        Covers both referential integrity (ids pointing at real entities) and
        structural well-formedness that the generated wire types deliberately
        leave loose. The generated models come from the OpenAPI spec, which
        types ``position``/``size`` as untyped arrays and no longer pins a
        minimum vertex count on faces, so a geometry can parse cleanly yet still
        be degenerate in ways that crash downstream in STL export, viz, or the
        solver. This method flags those cases client-side with a readable error
        that names the offending entity.

        Returns a list of human-readable error strings.
        Empty list = geometry is consistent.
        """
        errors: list[str] = []

        vertex_ids = {v.id for v in self.vertices}
        edge_ids = {e.id for e in self.edges}
        face_ids = {f.id for f in self.faces}
        group_ids = {g.id for g in self.groups}

        for vertex in self.vertices:
            if not _is_numeric_triple(vertex.position):
                errors.append(
                    f"vertex '{vertex.id}' position must be exactly 3 numeric "
                    f"values, got {vertex.position!r}"
                )

        if not _is_numeric_triple(self.bounding_box.size):
            errors.append(
                f"boundingBox size must be exactly 3 numeric values, got "
                f"{self.bounding_box.size!r}"
            )

        for edge in self.edges:
            if edge.v0 not in vertex_ids:
                errors.append(f"edge '{edge.id}' references unknown vertex '{edge.v0}'")
            if edge.v1 not in vertex_ids:
                errors.append(f"edge '{edge.id}' references unknown vertex '{edge.v1}'")
            if edge.face_ids is None:
                errors.append(f"edge '{edge.id}' has null faceIds")
            for fid in edge.face_ids or []:
                if fid not in face_ids:
                    errors.append(f"edge '{edge.id}' references unknown face '{fid}'")

        for face in self.faces:
            # A face needs at least 2 vertices. 2 is legitimate: commit f6e1a29
            # relaxed the minimum from 3 to 2 so axisymmetric (R-Z) cross-section
            # geometries can carry 2-vertex line-segment faces. Fewer than 2 is
            # always degenerate.
            if len(face.vertex_ids) < 2:
                errors.append(
                    f"face '{face.id}' has fewer than 2 vertices "
                    f"({len(face.vertex_ids)})"
                )
            for vid in face.vertex_ids:
                if vid not in vertex_ids:
                    errors.append(f"face '{face.id}' references unknown vertex '{vid}'")
            for eid in face.edge_ids:
                if eid not in edge_ids:
                    errors.append(f"face '{face.id}' references unknown edge '{eid}'")

        for group in self.groups:
            if group.face_ids is None:
                errors.append(f"group '{group.name}' has null faceIds")
            if group.edge_ids is None:
                errors.append(f"group '{group.name}' has null edgeIds")
            for fid in group.face_ids or []:
                if fid not in face_ids:
                    errors.append(
                        f"group '{group.name}' references unknown face '{fid}'"
                    )
            for eid in group.edge_ids or []:
                if eid not in edge_ids:
                    errors.append(
                        f"group '{group.name}' references unknown edge '{eid}'"
                    )

        for gid in self.group_order:
            if gid not in group_ids:
                errors.append(f"groupOrder references unknown group '{gid}'")

        seen_faces: dict[str, str] = {}
        for group in self.groups:
            for fid in group.face_ids or []:
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
