"""PyVista (VTK) backend for geometry visualisation."""

from __future__ import annotations

from typing import Any

import numpy as np

from ._common import PreparedMesh


def render(
    prepared: PreparedMesh,
    *,
    show: bool = True,
    title: str | None = None,
    opacity: float = 1.0,
) -> Any:
    """Render *prepared* mesh using PyVista."""
    try:
        import pyvista as pv  # ty: ignore[unresolved-import]
    except ImportError:
        raise ImportError(
            "pyvista is required for the 'pyvista' backend. "
            "Install it with: pip install 'ionforge[viz-pyvista]'"
        ) from None

    plotter = pv.Plotter(title=title or "ionforge geometry")

    if not prepared.faces:
        if show:
            plotter.show()
        return plotter

    # Build VTK-style face connectivity array: [3, i, j, k, 3, i, j, k, ...]
    n_faces = len(prepared.faces)
    connectivity = np.empty(n_faces * 4, dtype=np.int64)
    face_colors = np.empty((n_faces, 3), dtype=np.uint8)
    for fi, fd in enumerate(prepared.faces):
        offset = fi * 4
        connectivity[offset] = 3
        connectivity[offset + 1] = fd.vertex_indices[0]
        connectivity[offset + 2] = fd.vertex_indices[1]
        connectivity[offset + 3] = fd.vertex_indices[2]
        # Parse hex colour to RGB
        c = fd.color.lstrip("#")
        face_colors[fi] = [int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)]

    mesh = pv.PolyData(prepared.positions, connectivity)
    mesh.cell_data["colors"] = face_colors

    plotter.add_mesh(
        mesh,
        scalars="colors",
        rgb=True,
        opacity=opacity,
        show_scalar_bar=False,
    )

    plotter.add_axes()

    if show:
        plotter.show()
    return plotter
