"""Parametric geometry primitives for charged particle optics.

Each primitive generates a triangulated surface mesh as lists of
Vertex, Edge, and Face objects. Primitives are added to a Geometry
via its .add() method.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import Edge, Face, Vertex


def _ring(
    radius: float,
    z: float,
    n: int,
    offset: float = 0.0,
) -> list[tuple[float, float, float]]:
    """Generate n points on a circle at height z."""
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False) + offset
    return [(float(radius * np.cos(a)), float(radius * np.sin(a)), z) for a in angles]


@dataclass
class _MeshResult:
    """Raw mesh output from a primitive's .mesh() method."""

    vertices: list[Vertex]
    edges: list[Edge]
    faces: list[Face]


class Cylinder:
    """Cylindrical surface (open-ended).

    Generates a triangulated lateral surface with no end caps.
    Use AnnularDisk to cap the ends if needed.
    """

    def __init__(
        self,
        r: float,
        length: float,
        voltage: float | None = None,
        name: str = "cylinder",
        n_segments: int = 32,
    ) -> None:
        self.r = r
        self.length = length
        self.voltage = voltage
        self.name = name
        self.n_segments = n_segments

    def mesh(self, prefix: str, z_offset: float) -> _MeshResult:
        n = self.n_segments
        bottom = _ring(self.r, z_offset, n)
        top = _ring(self.r, z_offset + self.length, n)

        vertices = []
        for i, (b, t) in enumerate(zip(bottom, top, strict=True)):
            vertices.append(Vertex(id=f"{prefix}_vb{i}", position=b))
            vertices.append(Vertex(id=f"{prefix}_vt{i}", position=t))

        edges: list[Edge] = []
        faces: list[Face] = []

        for i in range(n):
            j = (i + 1) % n
            bi, ti = i * 2, i * 2 + 1
            bj, tj = j * 2, j * 2 + 1

            vb_i = vertices[bi].id
            vt_i = vertices[ti].id
            vb_j = vertices[bj].id
            vt_j = vertices[tj].id

            f0_id = f"{prefix}_f{i}a"
            f1_id = f"{prefix}_f{i}b"

            e0_id = f"{prefix}_e{i}_bot"
            e1_id = f"{prefix}_e{i}_diag"
            e2_id = f"{prefix}_e{i}_left"
            e3_id = f"{prefix}_e{i}_top"
            e4_id = f"{prefix}_e{i}_right"

            edges.extend(
                [
                    Edge(id=e0_id, v0=vb_i, v1=vb_j, face_ids=[f0_id]),
                    Edge(id=e1_id, v0=vb_j, v1=vt_i, face_ids=[f0_id, f1_id]),
                    Edge(id=e2_id, v0=vt_i, v1=vb_i, face_ids=[f0_id]),
                    Edge(id=e3_id, v0=vt_i, v1=vt_j, face_ids=[f1_id]),
                    Edge(id=e4_id, v0=vt_j, v1=vb_j, face_ids=[f1_id]),
                ]
            )

            faces.extend(
                [
                    Face(
                        id=f0_id,
                        vertex_ids=[vb_i, vb_j, vt_i],
                        edge_ids=[e0_id, e1_id, e2_id],
                    ),
                    Face(
                        id=f1_id,
                        vertex_ids=[vt_i, vt_j, vb_j],
                        edge_ids=[e3_id, e4_id, e1_id],
                    ),
                ]
            )

        return _MeshResult(vertices=vertices, edges=edges, faces=faces)


class AnnularDisk:
    """Flat annular disk (ring with a hole).

    Generates a triangulated ring surface in the xy-plane.
    Use for aperture plates, end caps, etc.
    """

    def __init__(
        self,
        inner_radius: float,
        outer_radius: float,
        voltage: float | None = None,
        name: str = "annular_disk",
        n_segments: int = 32,
    ) -> None:
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.voltage = voltage
        self.name = name
        self.n_segments = n_segments

    def mesh(self, prefix: str, z_offset: float) -> _MeshResult:
        n = self.n_segments
        inner = _ring(self.inner_radius, z_offset, n)
        outer = _ring(self.outer_radius, z_offset, n)

        vertices = []
        for i, (inn, out) in enumerate(zip(inner, outer, strict=True)):
            vertices.append(Vertex(id=f"{prefix}_vi{i}", position=inn))
            vertices.append(Vertex(id=f"{prefix}_vo{i}", position=out))

        edges: list[Edge] = []
        faces: list[Face] = []

        for i in range(n):
            j = (i + 1) % n
            ii, oi = i * 2, i * 2 + 1
            ij, oj = j * 2, j * 2 + 1

            vi_i = vertices[ii].id
            vo_i = vertices[oi].id
            vi_j = vertices[ij].id
            vo_j = vertices[oj].id

            f0_id = f"{prefix}_f{i}a"
            f1_id = f"{prefix}_f{i}b"

            e0_id = f"{prefix}_e{i}_inner"
            e1_id = f"{prefix}_e{i}_diag"
            e2_id = f"{prefix}_e{i}_left"
            e3_id = f"{prefix}_e{i}_outer"
            e4_id = f"{prefix}_e{i}_right"

            edges.extend(
                [
                    Edge(id=e0_id, v0=vi_i, v1=vi_j, face_ids=[f0_id]),
                    Edge(id=e1_id, v0=vi_j, v1=vo_i, face_ids=[f0_id, f1_id]),
                    Edge(id=e2_id, v0=vo_i, v1=vi_i, face_ids=[f0_id]),
                    Edge(id=e3_id, v0=vo_i, v1=vo_j, face_ids=[f1_id]),
                    Edge(id=e4_id, v0=vo_j, v1=vi_j, face_ids=[f1_id]),
                ]
            )

            faces.extend(
                [
                    Face(
                        id=f0_id,
                        vertex_ids=[vi_i, vi_j, vo_i],
                        edge_ids=[e0_id, e1_id, e2_id],
                    ),
                    Face(
                        id=f1_id,
                        vertex_ids=[vo_i, vo_j, vi_j],
                        edge_ids=[e3_id, e4_id, e1_id],
                    ),
                ]
            )

        return _MeshResult(vertices=vertices, edges=edges, faces=faces)


class Cone:
    """Conical (tapered) surface.

    Generates a triangulated lateral surface from bottom_radius to
    top_radius. Set one radius to 0 for a pointed cone (the tip
    collapses to a single vertex).
    """

    def __init__(
        self,
        bottom_radius: float,
        top_radius: float,
        length: float,
        voltage: float | None = None,
        name: str = "cone",
        n_segments: int = 32,
    ) -> None:
        self.bottom_radius = bottom_radius
        self.top_radius = top_radius
        self.length = length
        self.voltage = voltage
        self.name = name
        self.n_segments = n_segments

    def mesh(self, prefix: str, z_offset: float) -> _MeshResult:
        n = self.n_segments

        if self.top_radius == 0.0:
            return self._mesh_pointed(prefix, z_offset, tip_at_top=True)
        if self.bottom_radius == 0.0:
            return self._mesh_pointed(prefix, z_offset, tip_at_top=False)

        bottom = _ring(self.bottom_radius, z_offset, n)
        top = _ring(self.top_radius, z_offset + self.length, n)

        vertices = []
        for i, (b, t) in enumerate(zip(bottom, top, strict=True)):
            vertices.append(Vertex(id=f"{prefix}_vb{i}", position=b))
            vertices.append(Vertex(id=f"{prefix}_vt{i}", position=t))

        edges: list[Edge] = []
        faces: list[Face] = []

        for i in range(n):
            j = (i + 1) % n
            bi, ti = i * 2, i * 2 + 1
            bj, tj = j * 2, j * 2 + 1

            vb_i = vertices[bi].id
            vt_i = vertices[ti].id
            vb_j = vertices[bj].id
            vt_j = vertices[tj].id

            f0_id = f"{prefix}_f{i}a"
            f1_id = f"{prefix}_f{i}b"

            e0_id = f"{prefix}_e{i}_bot"
            e1_id = f"{prefix}_e{i}_diag"
            e2_id = f"{prefix}_e{i}_left"
            e3_id = f"{prefix}_e{i}_top"
            e4_id = f"{prefix}_e{i}_right"

            edges.extend(
                [
                    Edge(id=e0_id, v0=vb_i, v1=vb_j, face_ids=[f0_id]),
                    Edge(id=e1_id, v0=vb_j, v1=vt_i, face_ids=[f0_id, f1_id]),
                    Edge(id=e2_id, v0=vt_i, v1=vb_i, face_ids=[f0_id]),
                    Edge(id=e3_id, v0=vt_i, v1=vt_j, face_ids=[f1_id]),
                    Edge(id=e4_id, v0=vt_j, v1=vb_j, face_ids=[f1_id]),
                ]
            )

            faces.extend(
                [
                    Face(
                        id=f0_id,
                        vertex_ids=[vb_i, vb_j, vt_i],
                        edge_ids=[e0_id, e1_id, e2_id],
                    ),
                    Face(
                        id=f1_id,
                        vertex_ids=[vt_i, vt_j, vb_j],
                        edge_ids=[e3_id, e4_id, e1_id],
                    ),
                ]
            )

        return _MeshResult(vertices=vertices, edges=edges, faces=faces)

    def _mesh_pointed(
        self, prefix: str, z_offset: float, *, tip_at_top: bool
    ) -> _MeshResult:
        n = self.n_segments

        if tip_at_top:
            ring_r = self.bottom_radius
            ring_z = z_offset
            tip_z = z_offset + self.length
        else:
            ring_r = self.top_radius
            ring_z = z_offset + self.length
            tip_z = z_offset

        ring_pts = _ring(ring_r, ring_z, n)
        tip_pos = (0.0, 0.0, tip_z)

        vertices = [Vertex(id=f"{prefix}_tip", position=tip_pos)]
        for i, pt in enumerate(ring_pts):
            vertices.append(Vertex(id=f"{prefix}_vr{i}", position=pt))

        edges: list[Edge] = []
        faces: list[Face] = []

        for i in range(n):
            j = (i + 1) % n
            ri = i + 1  # +1 because tip is index 0
            rj = j + 1

            vr_i = vertices[ri].id
            vr_j = vertices[rj].id
            v_tip = vertices[0].id

            f_id = f"{prefix}_f{i}"
            e0_id = f"{prefix}_e{i}_ring"
            e1_id = f"{prefix}_e{i}_spoke_l"
            e2_id = f"{prefix}_e{i}_spoke_r"

            edges.extend(
                [
                    Edge(id=e0_id, v0=vr_i, v1=vr_j, face_ids=[f_id]),
                    Edge(id=e1_id, v0=vr_j, v1=v_tip, face_ids=[f_id]),
                    Edge(id=e2_id, v0=v_tip, v1=vr_i, face_ids=[f_id]),
                ]
            )

            faces.append(
                Face(
                    id=f_id,
                    vertex_ids=[vr_i, vr_j, v_tip],
                    edge_ids=[e0_id, e1_id, e2_id],
                )
            )

        return _MeshResult(vertices=vertices, edges=edges, faces=faces)


class Sphere:
    """UV-sphere surface.

    Generates a triangulated sphere using latitude/longitude subdivision.
    The poles use triangle fans; the middle bands use quad strips split
    into triangles.
    """

    def __init__(
        self,
        r: float,
        voltage: float | None = None,
        name: str = "sphere",
        n_segments: int = 32,
        n_rings: int = 16,
    ) -> None:
        self.r = r
        self.voltage = voltage
        self.name = name
        self.n_segments = n_segments
        self.n_rings = n_rings

    def mesh(self, prefix: str, z_offset: float) -> _MeshResult:
        n_seg = self.n_segments
        n_ring = self.n_rings
        r = self.r
        cz = z_offset  # sphere centered at (0, 0, z_offset)

        vertices: list[Vertex] = []
        v_id_map: dict[tuple[int, int], str] = {}

        # South pole
        south_id = f"{prefix}_south"
        vertices.append(Vertex(id=south_id, position=(0.0, 0.0, cz - r)))

        # Latitude rings (excluding poles)
        for ring_i in range(1, n_ring):
            phi = np.pi * ring_i / n_ring  # 0=north, pi=south
            ring_z = cz - r * np.cos(phi)  # south pole at bottom
            ring_r = r * np.sin(phi)
            for seg_j in range(n_seg):
                theta = 2 * np.pi * seg_j / n_seg
                x = float(ring_r * np.cos(theta))
                y = float(ring_r * np.sin(theta))
                vid = f"{prefix}_v{ring_i}_{seg_j}"
                v_id_map[(ring_i, seg_j)] = vid
                vertices.append(Vertex(id=vid, position=(x, y, float(ring_z))))

        # North pole
        north_id = f"{prefix}_north"
        vertices.append(Vertex(id=north_id, position=(0.0, 0.0, cz + r)))

        edges: list[Edge] = []
        faces: list[Face] = []
        fi = 0

        def _add_tri(va: str, vb: str, vc: str) -> None:
            nonlocal fi
            f_id = f"{prefix}_f{fi}"
            ea = f"{prefix}_e{fi}_a"
            eb = f"{prefix}_e{fi}_b"
            ec = f"{prefix}_e{fi}_c"
            edges.extend(
                [
                    Edge(id=ea, v0=va, v1=vb, face_ids=[f_id]),
                    Edge(id=eb, v0=vb, v1=vc, face_ids=[f_id]),
                    Edge(id=ec, v0=vc, v1=va, face_ids=[f_id]),
                ]
            )
            faces.append(Face(id=f_id, vertex_ids=[va, vb, vc], edge_ids=[ea, eb, ec]))
            fi += 1

        # South pole fan (ring_i=1 connects to south pole)
        # Ring index 1 is closest to south pole (phi = pi/n_ring)
        for j in range(n_seg):
            j_next = (j + 1) % n_seg
            _add_tri(south_id, v_id_map[(1, j)], v_id_map[(1, j_next)])

        # Middle bands
        for ring_i in range(1, n_ring - 1):
            for j in range(n_seg):
                j_next = (j + 1) % n_seg
                v00 = v_id_map[(ring_i, j)]
                v01 = v_id_map[(ring_i, j_next)]
                v10 = v_id_map[(ring_i + 1, j)]
                v11 = v_id_map[(ring_i + 1, j_next)]
                _add_tri(v00, v10, v01)
                _add_tri(v01, v10, v11)

        # North pole fan (ring_i=n_ring-1 connects to north pole)
        last_ring = n_ring - 1
        for j in range(n_seg):
            j_next = (j + 1) % n_seg
            _add_tri(v_id_map[(last_ring, j)], north_id, v_id_map[(last_ring, j_next)])

        return _MeshResult(vertices=vertices, edges=edges, faces=faces)
