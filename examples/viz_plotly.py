#!/usr/bin/env python3
"""Visualise geometry with plotly (interactive, great for Jupyter/Colab).

Install the extra first::

    uv add ionforge --extra viz-plotly

Usage::

    python examples/viz_plotly.py
"""

from __future__ import annotations

from ionforge.geometry import AnnularDisk, Cone, Cylinder, Geometry


def build_einzel_lens() -> Geometry:
    geo = Geometry(bounding_box=(0.06, 0.06, 0.12))
    geo.add(Cylinder(r=0.01, length=0.03, voltage=0, name="entry_tube"))
    geo.add(
        AnnularDisk(inner_radius=0.005, outer_radius=0.01, voltage=0, name="entry_plate"),
        z=0.03,
    )
    geo.add(
        Cone(bottom_radius=0.005, top_radius=0.008, length=0.005, voltage=-500, name="focus_taper"),
        z=0.03,
    )
    geo.add(Cylinder(r=0.008, length=0.02, voltage=-500, name="focus_tube"), z=0.035)
    geo.add(
        AnnularDisk(inner_radius=0.005, outer_radius=0.01, voltage=0, name="exit_plate"),
        z=0.06,
    )
    geo.add(Cylinder(r=0.01, length=0.03, voltage=0, name="exit_tube"), z=0.06)
    return geo


if __name__ == "__main__":
    geo = build_einzel_lens()
    geo.visualize(backend="plotly", color_by="voltage", title="Einzel Lens (plotly)")
