"""Matplotlib backend for geometry visualisation."""

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
    """Render *prepared* mesh using matplotlib's mplot3d."""
    try:
        import matplotlib.colors as mcolors
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError:
        raise ImportError(
            "matplotlib is required for the 'matplotlib' backend. "
            "Install it with: pip install matplotlib"
        ) from None

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    if not prepared.faces:
        # Empty geometry — just show the bounding box outline
        _draw_bounding_box(ax, prepared.bounding_box_size)
        if title:
            ax.set_title(title)
        if show:
            plt.show()
        return fig

    # Build polygon collection
    polygons: list[list[tuple[float, float, float]]] = []
    face_colors: list[Any] = []
    for fd in prepared.faces:
        tri = [tuple(prepared.positions[i]) for i in fd.vertex_indices]
        polygons.append(tri)
        rgba = mcolors.to_rgba(fd.color, alpha=opacity)
        face_colors.append(rgba)

    poly = Poly3DCollection(
        polygons, facecolors=face_colors, edgecolors="k", linewidths=0.1
    )
    ax.add_collection3d(poly)

    # Set axis limits from mesh extents
    xs = prepared.positions[:, 0]
    ys = prepared.positions[:, 1]
    zs = prepared.positions[:, 2]
    max_range = max(np.ptp(xs), np.ptp(ys), np.ptp(zs)) / 2 or 0.01
    mid_x = (xs.max() + xs.min()) / 2
    mid_y = (ys.max() + ys.min()) / 2
    mid_z = (zs.max() + zs.min()) / 2
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")

    # Legend with group patches
    import matplotlib.patches as mpatches

    legend_handles = [
        mpatches.Patch(color=g.color, label=g.name) for g in prepared.groups
    ]
    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper left", fontsize="small")

    if title:
        ax.set_title(title)

    fig.tight_layout()
    if show:
        plt.show()
    return fig


def _draw_bounding_box(
    ax: Any,
    size: tuple[float, float, float],
) -> None:
    """Draw a wireframe box centred at the origin."""
    sx, sy, sz = [s / 2 for s in size]
    # 12 edges of a box
    lw = 0.5
    for s in (-1, 1):
        for t in (-1, 1):
            ax.plot3D(
                [s * sx, s * sx],
                [t * sy, t * sy],
                [-sz, sz],
                color="grey",
                linewidth=lw,
            )
            ax.plot3D(
                [s * sx, s * sx],
                [-sy, sy],
                [t * sz, t * sz],
                color="grey",
                linewidth=lw,
            )
            ax.plot3D(
                [-sx, sx],
                [s * sy, s * sy],
                [t * sz, t * sz],
                color="grey",
                linewidth=lw,
            )
