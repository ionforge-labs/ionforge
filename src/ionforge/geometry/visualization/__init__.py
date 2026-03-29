"""Geometry visualisation with pluggable backends.

Usage via the :class:`~ionforge.geometry.Geometry` builder::

    geo.visualize()                          # matplotlib (default)
    geo.visualize(backend="plotly")          # interactive Jupyter/Colab
    geo.visualize(backend="pyvista")         # full VTK 3-D

Or standalone with a :class:`~ionforge.geometry.SerializedGeometry`::

    from ionforge.geometry.visualization import render
    render(serialized_geometry, backend="plotly", color_by="voltage")
"""

from __future__ import annotations

from typing import Any

from ..models import SerializedGeometry
from ._common import prepare_mesh, resolve_color_by

__all__ = ["render"]


def render(
    sg: SerializedGeometry,
    *,
    backend: str = "matplotlib",
    color_by: str | None = None,
    show: bool = True,
    title: str | None = None,
    opacity: float = 1.0,
) -> Any:
    """Render a :class:`SerializedGeometry` with the chosen backend.

    Parameters
    ----------
    sg:
        The geometry to render.
    backend:
        ``"matplotlib"`` (default), ``"plotly"``, or ``"pyvista"``.
    color_by:
        ``"group"`` uses each group's hex colour.  ``"voltage"`` applies a
        diverging blue–white–red colourmap.  ``None`` (default) auto-selects
        ``"voltage"`` when every group has a voltage assigned, otherwise
        ``"group"``.
    show:
        If *True* (default), display the figure immediately.
    title:
        Optional figure title.
    opacity:
        Surface opacity (0 = transparent, 1 = opaque).

    Returns
    -------
    Backend-specific figure object (``matplotlib.figure.Figure``,
    ``plotly.graph_objects.Figure``, or ``pyvista.Plotter``).
    """
    resolved = resolve_color_by(sg, color_by)
    prepared = prepare_mesh(sg, resolved)

    if backend == "matplotlib":
        from ._matplotlib import render as _render
    elif backend == "plotly":
        from ._plotly import render as _render
    elif backend == "pyvista":
        from ._pyvista import render as _render
    else:
        msg = (
            f"Unknown backend {backend!r}. Choose 'matplotlib', 'plotly', or 'pyvista'."
        )
        raise ValueError(msg)

    return _render(prepared, show=show, title=title, opacity=opacity)
