"""STL Mesh Import for IonForge 3D BEM.

Loads triangulated surfaces from STL files and feeds them into BEMSolver3D
as FlatTriangularPatch panels.

Supports both ASCII and binary STL formats.

Requires the ``stl`` extra::

    uv add "ionforge[stl]"
"""

from __future__ import annotations

import struct
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import numpy as np
except ImportError as exc:
    raise ImportError(
        "numpy is required for STL support. Install it with: uv add 'ionforge[stl]'"
    ) from exc

if TYPE_CHECKING:
    from typing import Any


# ------------------------------------------------------------------
# STL loading
# ------------------------------------------------------------------


def load_stl(
    filename: str,
    scale_factor: float = 1.0,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Load a triangulated surface from an STL file.

    Supports both ASCII and binary STL formats.

    Parameters
    ----------
    filename
        Path to .stl file.
    scale_factor
        Multiply all coordinates by this factor
        (e.g. 1e-3 to convert mm to metres).

    Returns
    -------
    list of (v1, v2, v3) tuples, each vertex is ndarray of shape (3,).
    """
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"STL file not found: {filename}")

    with open(path, "rb") as f:
        header = f.read(80)

    if header[:5] == b"solid" and _is_ascii_stl(path):
        triangles = _load_ascii_stl(path)
    else:
        triangles = _load_binary_stl(path)

    if scale_factor != 1.0:
        triangles = [
            (v1 * scale_factor, v2 * scale_factor, v3 * scale_factor)
            for v1, v2, v3 in triangles
        ]

    return triangles


def _is_ascii_stl(path: Path) -> bool:
    """Check if STL is ASCII by looking for 'endsolid' keyword."""
    try:
        with open(path, errors="replace") as f:
            content = f.read(1024)
        return "endsolid" in content or "facet" in content
    except Exception:
        return False


def _load_ascii_stl(
    path: Path,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Parse ASCII STL format."""
    triangles: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    with open(path, errors="replace") as f:
        lines = f.readlines()

    vertices: list[np.ndarray] = []
    for line in lines:
        line = line.strip()
        if line.startswith("vertex"):
            coords = [float(x) for x in line.split()[1:4]]
            vertices.append(np.array(coords))
        elif line.startswith("endfacet"):
            if len(vertices) >= 3:
                triangles.append((vertices[0], vertices[1], vertices[2]))
            vertices = []

    if not triangles:
        raise ValueError(f"No triangles found in ASCII STL: {path}")

    return triangles


def _load_binary_stl(
    path: Path,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Parse binary STL format."""
    with open(path, "rb") as f:
        f.read(80)  # 80-byte header (skip)
        n_tris = struct.unpack("<I", f.read(4))[0]

        triangles: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        for _ in range(n_tris):
            f.read(12)  # normal vector (skip — we recompute)
            v1 = np.frombuffer(f.read(12), dtype=np.float32).astype(float)
            v2 = np.frombuffer(f.read(12), dtype=np.float32).astype(float)
            v3 = np.frombuffer(f.read(12), dtype=np.float32).astype(float)
            f.read(2)  # attribute byte count (skip)
            triangles.append((v1.copy(), v2.copy(), v3.copy()))

    if not triangles:
        raise ValueError(f"No triangles found in binary STL: {path}")

    return triangles


# ------------------------------------------------------------------
# Mesh validation and statistics
# ------------------------------------------------------------------


def mesh_stats(
    triangles: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    verbose: bool = True,
) -> dict[str, Any]:
    """Compute mesh quality statistics.

    Returns dict with: n_triangles, total_area, min_area, max_area,
    min_edge, max_edge, mean_aspect_ratio, n_degenerate.
    """
    areas: list[float] = []
    edges: list[float] = []
    aspects: list[float] = []
    n_degen = 0

    for v1, v2, v3 in triangles:
        e1 = float(np.linalg.norm(v2 - v1))
        e2 = float(np.linalg.norm(v3 - v2))
        e3 = float(np.linalg.norm(v1 - v3))
        area = 0.5 * float(np.linalg.norm(np.cross(v2 - v1, v3 - v1)))

        if area < 1e-30 or max(e1, e2, e3) < 1e-30:
            n_degen += 1
            continue

        areas.append(area)
        edges.extend([e1, e2, e3])
        l_max = max(e1, e2, e3)
        aspects.append(l_max**2 / (2.0 * area))

    stats: dict[str, Any] = {
        "n_triangles": len(triangles),
        "n_degenerate": n_degen,
        "n_valid": len(areas),
        "total_area": sum(areas),
        "min_area": min(areas) if areas else 0.0,
        "max_area": max(areas) if areas else 0.0,
        "min_edge": min(edges) if edges else 0.0,
        "max_edge": max(edges) if edges else 0.0,
        "mean_aspect": float(np.mean(aspects)) if aspects else 0.0,
        "max_aspect": max(aspects) if aspects else 0.0,
    }

    if verbose:
        print("Mesh statistics:")
        print(
            f"  Triangles: {stats['n_triangles']}  "
            f"({stats['n_degenerate']} degenerate, "
            f"{stats['n_valid']} valid)"
        )
        print(f"  Total area: {stats['total_area'] * 1e6:.2f} mm²")
        print(
            f"  Edge range: {stats['min_edge'] * 1e3:.3f} – "
            f"{stats['max_edge'] * 1e3:.3f} mm"
        )
        print(
            f"  Aspect ratio: mean={stats['mean_aspect']:.2f}  "
            f"max={stats['max_aspect']:.2f}"
        )
        if stats["max_aspect"] > 10:
            warnings.warn(
                f"High aspect ratio triangles (max={stats['max_aspect']:.1f}) "
                "may reduce BEM accuracy.  Consider remeshing.",
                UserWarning,
                stacklevel=2,
            )

    return stats


# ------------------------------------------------------------------
# STL writer
# ------------------------------------------------------------------


def write_stl(
    filename: str,
    triangles: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    name: str = "ionforge_mesh",
) -> None:
    """Write triangles to binary STL file."""
    with open(filename, "wb") as f:
        header = name.encode("ascii")[:80].ljust(80, b"\x00")
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for v1, v2, v3 in triangles:
            v1, v2, v3 = (
                np.array(v1, float),
                np.array(v2, float),
                np.array(v3, float),
            )
            normal = np.cross(v2 - v1, v3 - v1)
            n_len = float(np.linalg.norm(normal))
            normal = normal / n_len if n_len > 1e-30 else np.array([0.0, 0.0, 1.0])
            f.write(struct.pack("<fff", *normal.astype(np.float32)))
            f.write(struct.pack("<fff", *v1.astype(np.float32)))
            f.write(struct.pack("<fff", *v2.astype(np.float32)))
            f.write(struct.pack("<fff", *v3.astype(np.float32)))
            f.write(struct.pack("<H", 0))
