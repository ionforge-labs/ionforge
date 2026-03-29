#!/usr/bin/env python3
"""Example: visualise a simple Einzel lens geometry.

Usage::

    python examples/visualize_geometry.py
    python examples/visualize_geometry.py --backend plotly
    python examples/visualize_geometry.py --color-by voltage
"""

from __future__ import annotations

import argparse

from ionforge.geometry import AnnularDisk, Cone, Cylinder, Geometry


def build_einzel_lens() -> Geometry:
    """Build a three-element Einzel lens with drift tubes and aperture plates."""
    geo = Geometry(bounding_box=(0.06, 0.06, 0.12))

    # Entry drift tube
    geo.add(Cylinder(r=0.01, length=0.03, voltage=0, name="entry_tube"))

    # Entry aperture plate
    geo.add(
        AnnularDisk(
            inner_radius=0.005, outer_radius=0.01, voltage=0, name="entry_plate"
        ),
        z=0.03,
    )

    # Focus electrode (tapered entry)
    geo.add(
        Cone(
            bottom_radius=0.005,
            top_radius=0.008,
            length=0.005,
            voltage=-500,
            name="focus_taper",
        ),
        z=0.03,
    )

    # Focus electrode (cylinder)
    geo.add(
        Cylinder(r=0.008, length=0.02, voltage=-500, name="focus_tube"),
        z=0.035,
    )

    # Exit aperture plate
    geo.add(
        AnnularDisk(
            inner_radius=0.005, outer_radius=0.01, voltage=0, name="exit_plate"
        ),
        z=0.06,
    )

    # Exit drift tube
    geo.add(Cylinder(r=0.01, length=0.03, voltage=0, name="exit_tube"), z=0.06)

    return geo


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualise an Einzel lens geometry")
    parser.add_argument(
        "--backend",
        choices=["matplotlib", "plotly", "pyvista"],
        default="matplotlib",
    )
    parser.add_argument(
        "--color-by",
        choices=["group", "voltage"],
        default=None,
    )
    args = parser.parse_args()

    geo = build_einzel_lens()
    geo.visualize(
        backend=args.backend,
        color_by=args.color_by,
        title="Einzel Lens",
    )


if __name__ == "__main__":
    main()
