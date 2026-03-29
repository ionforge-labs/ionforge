#!/usr/bin/env python3
"""Generate README images from the Einzel lens example geometry."""

from __future__ import annotations

from pathlib import Path

from ionforge.geometry import AnnularDisk, Cone, Cylinder, Geometry

IMAGES_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"


def build_einzel_lens() -> Geometry:
    geo = Geometry(bounding_box=(0.06, 0.06, 0.12))
    geo.add(Cylinder(r=0.01, length=0.03, voltage=0, name="entry_tube"))
    geo.add(
        AnnularDisk(
            inner_radius=0.005,
            outer_radius=0.01,
            voltage=0,
            name="entry_plate",
        ),
        z=0.03,
    )
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
    geo.add(
        Cylinder(r=0.008, length=0.02, voltage=-500, name="focus_tube"),
        z=0.035,
    )
    geo.add(
        AnnularDisk(
            inner_radius=0.005,
            outer_radius=0.01,
            voltage=0,
            name="exit_plate",
        ),
        z=0.06,
    )
    geo.add(
        Cylinder(r=0.01, length=0.03, voltage=0, name="exit_tube"),
        z=0.06,
    )
    return geo


def main() -> None:
    import matplotlib

    matplotlib.use("Agg")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    geo = build_einzel_lens()

    # Voltage colourmap
    fig = geo.visualize(
        backend="matplotlib",
        color_by="voltage",
        title="Einzel Lens — colour by voltage",
        show=False,
    )
    fig.savefig(IMAGES_DIR / "viz_voltage.png", dpi=150, bbox_inches="tight")
    print(f"Saved {IMAGES_DIR / 'viz_voltage.png'}")

    # Group colours
    fig = geo.visualize(
        backend="matplotlib",
        color_by="group",
        title="Einzel Lens — colour by group",
        show=False,
    )
    fig.savefig(IMAGES_DIR / "viz_group.png", dpi=150, bbox_inches="tight")
    print(f"Saved {IMAGES_DIR / 'viz_group.png'}")


if __name__ == "__main__":
    main()
