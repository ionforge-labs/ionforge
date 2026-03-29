"""Plotly backend for geometry visualisation."""

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
    """Render *prepared* mesh using Plotly Mesh3d traces."""
    try:
        import plotly.graph_objects as go  # ty: ignore[unresolved-import]
    except ImportError:
        raise ImportError(
            "plotly is required for the 'plotly' backend. "
            "Install it with: pip install 'ionforge[viz-plotly]'"
        ) from None

    fig = go.Figure()

    if not prepared.faces:
        fig.update_layout(title=title or "Empty geometry")
        if show:
            fig.show()
        return fig

    # Group faces by their group index for separate traces
    # Build a mapping: group_index -> list of face indices
    group_face_map: dict[int, list[int]] = {}
    face_group_idx: list[int] = []
    for fi, fd in enumerate(prepared.faces):
        # Find which group this face colour belongs to
        gi = _find_group_index(fd.color, prepared.groups)
        face_group_idx.append(gi)
        group_face_map.setdefault(gi, []).append(fi)

    # One Mesh3d trace per group
    for gi, group in enumerate(prepared.groups):
        fi_list = group_face_map.get(gi, [])
        if not fi_list:
            continue

        # Collect unique vertex indices used by this group's faces
        used_verts: set[int] = set()
        for fi in fi_list:
            used_verts.update(prepared.faces[fi].vertex_indices)
        sorted_verts = sorted(used_verts)
        old_to_new = {old: new for new, old in enumerate(sorted_verts)}

        pos = prepared.positions[sorted_verts]
        i_arr = []
        j_arr = []
        k_arr = []
        for fi in fi_list:
            v0, v1, v2 = prepared.faces[fi].vertex_indices
            i_arr.append(old_to_new[v0])
            j_arr.append(old_to_new[v1])
            k_arr.append(old_to_new[v2])

        fig.add_trace(
            go.Mesh3d(
                x=pos[:, 0],
                y=pos[:, 1],
                z=pos[:, 2],
                i=np.array(i_arr),
                j=np.array(j_arr),
                k=np.array(k_arr),
                color=group.color,
                opacity=opacity,
                name=group.name,
                showlegend=True,
            )
        )

    fig.update_layout(
        title=title,
        scene={
            "xaxis_title": "X (m)",
            "yaxis_title": "Y (m)",
            "zaxis_title": "Z (m)",
            "aspectmode": "data",
        },
    )

    if show:
        fig.show()
    return fig


def _find_group_index(color: str, groups: list[Any]) -> int:
    """Return the index of the group whose colour matches *color*."""
    for i, g in enumerate(groups):
        if g.color == color:
            return i
    return 0
