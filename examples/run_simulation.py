"""End-to-end example: simulate an einzel lens on the IonForge cloud API.

This is the full workflow a physicist follows to run a simulation in the
cloud, from a locally-built geometry to downloaded result files:

    1. build a three-electrode einzel lens with the SDK geometry primitives
    2. validate the geometry locally
    3. upload it to a project
    4. create a model and launch a run with explicit beam and solver params
    5. wait for the run to reach a terminal state
    6. download the result files

Run it with::

    export IONFORGE_API_KEY="ifk_..."
    uv add "ionforge[client]"
    uv run python examples/run_simulation.py --project-id proj_123

If ``--project-id`` is omitted a new project is created for you.

Units follow the SDK conventions: lengths in metres and voltages in volts
(SI), while beam energies use electron-volts, matching the API's beam model.

Every simulation parameter set below (beam, solver, and the other
``ModelParams`` blocks) is documented field-by-field, with units and defaults,
in ``docs/parameters.md``.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import TYPE_CHECKING

from ionforge.geometry import AnnularDisk, Cylinder, Geometry

if TYPE_CHECKING:
    from ionforge._types._generated import ModelParams

# --- Einzel lens dimensions (metres) --------------------------------------
# Three coaxial cylindrical tube electrodes sharing a common axis (z). The two
# outer tubes are held at ground; the centre tube sits at a focusing potential.
# Thin annular aperture plates cap the entrance and exit to define the beam.
BORE_RADIUS = 0.010  # tube inner radius (10 mm)
TUBE_LENGTH = 0.040  # length of each tube electrode (40 mm)
GAP = 0.005  # axial gap between adjacent tubes (5 mm)
APERTURE_INNER = 0.004  # aperture bore radius (4 mm)
APERTURE_OUTER = 0.020  # aperture plate outer radius (20 mm)

# --- Electrode potentials (volts) -----------------------------------------
GROUND_VOLTAGE = 0.0
# Centre electrode potential. An einzel lens focuses regardless of polarity;
# a negative centre potential gives a decelerating (accelerating-again) lens
# for a positive ion beam.
CENTRE_VOLTAGE = -2000.0


def build_einzel_geometry() -> Geometry:
    """Build a three-tube einzel lens with entrance and exit apertures.

    The electrodes are stacked along the z axis: an entrance aperture, then
    ground / focusing / ground tubes separated by small gaps, then an exit
    aperture. Returns the builder so the caller can also validate or upload it.

    Every electrode is a coaxial tube or disk, so the lens is rotationally
    symmetric about the z axis and is marked ``symmetry="axisymmetric"``.
    """
    # Total column length plus head-room for the bounding box.
    column_length = 3 * TUBE_LENGTH + 2 * GAP
    box = (0.06, 0.06, column_length + 0.06)
    geo = Geometry(bounding_box=box, symmetry="axisymmetric")

    # Entrance aperture plate at the front of the column.
    entrance_z = 0.010
    geo.add(
        AnnularDisk(
            inner_radius=APERTURE_INNER,
            outer_radius=APERTURE_OUTER,
            voltage=GROUND_VOLTAGE,
            name="entrance_aperture",
        ),
        z=entrance_z,
    )

    # Three coaxial tube electrodes.
    z0 = entrance_z + 0.010
    geo.add(
        Cylinder(
            r=BORE_RADIUS, length=TUBE_LENGTH, voltage=GROUND_VOLTAGE, name="tube_in"
        ),
        z=z0,
    )
    z1 = z0 + TUBE_LENGTH + GAP
    geo.add(
        Cylinder(
            r=BORE_RADIUS,
            length=TUBE_LENGTH,
            voltage=CENTRE_VOLTAGE,
            name="tube_centre",
        ),
        z=z1,
    )
    z2 = z1 + TUBE_LENGTH + GAP
    geo.add(
        Cylinder(
            r=BORE_RADIUS, length=TUBE_LENGTH, voltage=GROUND_VOLTAGE, name="tube_out"
        ),
        z=z2,
    )

    # Exit aperture plate just past the final tube.
    geo.add(
        AnnularDisk(
            inner_radius=APERTURE_INNER,
            outer_radius=APERTURE_OUTER,
            voltage=GROUND_VOLTAGE,
            name="exit_aperture",
        ),
        z=z2 + TUBE_LENGTH + 0.010,
    )

    return geo


def build_model_params() -> ModelParams:
    """Build explicit beam and solver parameters for the simulation.

    Uses the axisymmetric boundary-element solver, appropriate for a rotationally
    symmetric einzel lens, and a monoenergetic proton beam launched on-axis.
    """
    from ionforge.client import BeamParams, ModelParams, SolverParams

    return ModelParams(
        solver=SolverParams(solver_type="bem_axisym"),
        beam=BeamParams(
            e_nominal=1000.0,  # nominal beam energy, electron-volts (1 keV)
            mass_amu=1.0,  # proton
            charge_number=1,
            n_particles=200,
            angle_fwhm_deg=1.0,  # small angular spread
            seed=42,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-id",
        default=None,
        help="Existing project to use; a new project is created if omitted.",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to write downloaded result files into.",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("IONFORGE_API_KEY")
    if not api_key:
        print(
            "IONFORGE_API_KEY is not set. Export an API key first:\n"
            '    export IONFORGE_API_KEY="ifk_..."',
            file=sys.stderr,
        )
        return 1

    try:
        from ionforge.client import IonForge
    except ImportError:
        print(
            "The IonForge API client is not installed. Install the extra:\n"
            '    uv add "ionforge[client]"    # or: pip install "ionforge[client]"',
            file=sys.stderr,
        )
        return 1

    # 1. Build the geometry locally.
    print("Building einzel lens geometry ...")
    geo = build_einzel_geometry()

    # 2. Validate it before spending an upload on a broken mesh.
    serialized = geo.to_serialized_geometry()
    errors = serialized.validate_consistency()
    if errors:
        print("Geometry is not consistent:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    missing = serialized.all_groups_have_voltage()
    if missing:
        print(f"Electrodes missing a voltage: {missing}", file=sys.stderr)
        return 1
    print(
        f"  {len(serialized.vertices)} vertices, "
        f"{len(serialized.faces)} faces, "
        f"{len(serialized.groups)} electrodes -- consistent."
    )

    with IonForge() as client:  # reads IONFORGE_API_KEY from the environment
        # 3. Resolve a project and upload the geometry.
        project_id = args.project_id
        if project_id is None:
            project = client.projects.create(name="Einzel lens study")
            project_id = project.id
            print(f"Created project {project_id}")
        else:
            print(f"Using project {project_id}")

        print("Uploading geometry ...")
        geometry = client.upload_geometry(project_id, "einzel-lens-v1", geo)
        print(f"  uploaded geometry {geometry.id}")

        # 4. + 5. Create a model, launch a run with explicit params, and wait.
        print("Launching simulation run (this may take a while) ...")
        run = client.run_simulation(
            project_id=project_id,
            name="einzel-baseline",
            geometry_id=geometry.id,
            params=build_model_params(),
            run_name="baseline",
            wait=True,
        )
        print(f"  run {run.id} finished with status: {run.status}")
        if run.status != "completed":
            print(f"Run did not complete cleanly: {run.error_message}", file=sys.stderr)
            return 1

        # 6. Download the result files.
        print(f"Downloading results into {args.output_dir}/ ...")
        paths = client.download_results(run.id, output_dir=args.output_dir)
        for path in paths:
            print(f"  wrote {path}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
