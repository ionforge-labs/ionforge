"""Shared utilities for geometry visualisation backends."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..models import SerializedGeometry, Vec3

# ------------------------------------------------------------------
# Data structures consumed by every backend
# ------------------------------------------------------------------


@dataclass
class FaceData:
    """A single triangular face ready for rendering."""

    vertex_indices: tuple[int, int, int]
    color: str  # resolved hex colour


@dataclass
class GroupInfo:
    """Legend / metadata for one electrode group."""

    name: str
    color: str  # hex colour used for this group in the current render
    voltage: float | None


@dataclass
class PreparedMesh:
    """Backend-agnostic mesh data produced by :func:`prepare_mesh`."""

    positions: np.ndarray  # (N, 3) float64
    faces: list[FaceData]
    groups: list[GroupInfo]
    bounding_box_size: Vec3


# ------------------------------------------------------------------
# Colour helpers
# ------------------------------------------------------------------

_GREY = "#808080"


def voltage_to_color(
    voltage: float | None,
    vmin: float,
    vmax: float,
) -> str:
    """Map a voltage scalar to a hex colour on a diverging blue–white–red scale.

    * ``None`` → grey (#808080).
    * ``vmin == vmax`` → white.
    * Mixed signs → symmetric diverging scale centred at 0.
    * All non-negative → white → red.
    * All non-positive → blue → white.
    """
    if voltage is None:
        return _GREY
    if vmin == vmax:
        return "#ffffff"

    if vmin >= 0:
        # white → red
        t = (voltage - vmin) / (vmax - vmin) if vmax > vmin else 0.0
        r, g, b = 1.0, 1.0 - t, 1.0 - t
    elif vmax <= 0:
        # blue → white
        t = (voltage - vmin) / (vmax - vmin) if vmax > vmin else 0.0
        r, g, b = t, t, 1.0
    else:
        # diverging: blue(-1) → white(0) → red(+1)
        absmax = max(abs(vmin), abs(vmax))
        t = voltage / absmax  # -1 .. +1
        if t < 0:
            r, g, b = 1.0 + t, 1.0 + t, 1.0
        else:
            r, g, b = 1.0, 1.0 - t, 1.0 - t

    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


# ------------------------------------------------------------------
# Mesh preparation
# ------------------------------------------------------------------


def resolve_color_by(sg: SerializedGeometry, color_by: str | None) -> str:
    """Pick a colour mode, auto-detecting when *color_by* is ``None``."""
    if color_by is not None:
        if color_by not in ("group", "voltage"):
            msg = f"color_by must be 'group', 'voltage', or None, got {color_by!r}"
            raise ValueError(msg)
        return color_by
    # Auto: voltage if every group has one, else group colours.
    return "voltage" if not sg.all_groups_have_voltage() else "group"


def prepare_mesh(
    sg: SerializedGeometry,
    color_by: str,
) -> PreparedMesh:
    """Convert a :class:`SerializedGeometry` into backend-agnostic render data."""
    # Vertex id → integer index + positions array
    vid_to_idx: dict[str, int] = {}
    positions = np.empty((len(sg.vertices), 3), dtype=np.float64)
    for i, v in enumerate(sg.vertices):
        vid_to_idx[v.id] = i
        positions[i] = v.position

    # Face id → group mapping
    fid_to_group: dict[str, int] = {}
    for gi, group in enumerate(sg.groups):
        for fid in group.face_ids:
            fid_to_group[fid] = gi

    # Compute voltage range (only non-None values)
    voltages = [g.voltage for g in sg.groups if g.voltage is not None]
    vmin = min(voltages) if voltages else 0.0
    vmax = max(voltages) if voltages else 0.0

    # Resolve per-group colours
    group_colors: list[str] = []
    for group in sg.groups:
        if color_by == "voltage":
            group_colors.append(voltage_to_color(group.voltage, vmin, vmax))
        else:
            group_colors.append(group.color)

    # Build face list
    face_data: list[FaceData] = []
    for face in sg.faces:
        indices = tuple(vid_to_idx[vid] for vid in face.vertex_ids[:3])
        gi = fid_to_group.get(face.id)
        color = group_colors[gi] if gi is not None else _GREY
        face_data.append(
            FaceData(vertex_indices=indices, color=color)  # type: ignore[arg-type]
        )

    groups_info = [
        GroupInfo(name=g.name, color=group_colors[i], voltage=g.voltage)
        for i, g in enumerate(sg.groups)
    ]

    return PreparedMesh(
        positions=positions,
        faces=face_data,
        groups=groups_info,
        bounding_box_size=sg.bounding_box.size,
    )
