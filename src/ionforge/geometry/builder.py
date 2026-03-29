"""High-level geometry builder for charged particle optics simulations."""

from __future__ import annotations

from .models import BoundingBox, Edge, Face, Group, SerializedGeometry, Vec3, Vertex
from .primitives import AnnularDisk, Cone, Cylinder, Sphere, _MeshResult

Primitive = Cylinder | AnnularDisk | Cone | Sphere


class Geometry:
    """Accumulates primitives and produces a SerializedGeometry.

    Usage::

        geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube"))
        geo.add(AnnularDisk(inner_radius=0.005, outer_radius=0.01, voltage=0), z=0.06)
        serialized = geo.to_serialized_geometry()
    """

    def __init__(self, bounding_box: Vec3, bounding_box_voltage: float = 0.0) -> None:
        self._bounding_box = BoundingBox(
            size=bounding_box, voltage=bounding_box_voltage
        )
        self._groups: list[_PendingGroup] = []

    def add(self, primitive: Primitive, z: float = 0.0) -> None:
        """Add a primitive to the geometry at the given z position."""
        self._groups.append(_PendingGroup(primitive=primitive, z=z))

    def to_serialized_geometry(self) -> SerializedGeometry:
        """Build the final SerializedGeometry from all added primitives."""
        all_vertices: list[Vertex] = []
        all_edges: list[Edge] = []
        all_faces: list[Face] = []
        groups: list[Group] = []
        group_order: list[str] = []

        # Track name collisions
        name_counts: dict[str, int] = {}
        for pg in self._groups:
            name = pg.primitive.name
            name_counts[name] = name_counts.get(name, 0) + 1

        name_seen: dict[str, int] = {}
        for idx, pg in enumerate(self._groups):
            base_name = pg.primitive.name
            name_seen[base_name] = name_seen.get(base_name, 0) + 1

            if name_counts[base_name] > 1:
                unique_name = f"{base_name}_{name_seen[base_name]}"
            else:
                unique_name = base_name

            prefix = f"p{idx}"
            mesh: _MeshResult = pg.primitive.mesh(prefix, pg.z)

            all_vertices.extend(mesh.vertices)
            all_edges.extend(mesh.edges)
            all_faces.extend(mesh.faces)

            group_id = f"g{idx}"
            face_ids = [f.id for f in mesh.faces]

            groups.append(
                Group(
                    id=group_id,
                    name=unique_name,
                    color=_DEFAULT_COLORS[idx % len(_DEFAULT_COLORS)],
                    voltage=pg.primitive.voltage,
                    face_ids=face_ids,
                )
            )
            group_order.append(group_id)

        return SerializedGeometry(
            vertices=all_vertices,
            edges=all_edges,
            faces=all_faces,
            bounding_box=self._bounding_box,
            groups=groups,
            group_order=group_order,
        )


class _PendingGroup:
    __slots__ = ("primitive", "z")

    def __init__(self, primitive: Primitive, z: float) -> None:
        self.primitive = primitive
        self.z = z


_DEFAULT_COLORS = [
    "#e6194b",
    "#3cb44b",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#42d4f4",
    "#f032e6",
    "#bfef45",
    "#fabed4",
    "#469990",
    "#dcbeff",
    "#9a6324",
]
