# Simulation parameter reference

This document describes every field of the simulation parameter models you can
set through `ModelParams` when creating or running a model on the IonForge
cloud API. It is written for someone translating a setup from a paper into a
runnable simulation: each field lists its type, default, units, physical
meaning, and when you would change it.

`ModelParams` groups the settings into blocks:

| Block | Model | Purpose |
|---|---|---|
| `solver` | `SolverParams` | Which field solver to use and how finely to discretise it |
| `beam` | `BeamParams` | The particle source: species, energy, spread, sampling |
| `integrator` | `IntegratorParams` | Adaptive time stepping for trajectory integration |
| `ensemble` | `EnsembleParams` | Where particles terminate and how they are scored |
| `space_charge` | `SpaceChargeParams` | Optional self-consistent space-charge solve |
| `magnetic_field` | `MagneticFieldParams` | Optional static magnetic field from coils |
| `symmetry` | mirror hint (`mirrorMode`) | Mirror-plane symmetry hints for the solver |
| `fast_adjust` | `FastAdjust` | Per-electrode voltage overrides |
| `callbacks` | `Callbacks` | Per-step forces and time-varying drives |

Every block is optional; omit a block to accept solver defaults for it.

## Conventions

### Units

All geometric and field quantities are **SI** unless a field name says
otherwise:

| Quantity | Unit | Notes |
|---|---|---|
| Length, position, radius | metre (m) | includes grid bounds and coil geometry |
| Voltage | volt (V) | electrode potentials, RF amplitudes |
| Magnetic field / coil current | ampere (A) | coil `I`; field derives from Biot–Savart |
| Time, time step | second (s) | integrator steps, `t_max` |
| Beam energy (`E_nominal`, `dE_fwhm`) | electron-volt (eV) | kinetic energy, **not** joules |
| Angular spread (`*_deg`) | degree | only where the name ends in `_deg` |
| Mass (`mass_amu`) | atomic mass unit (u) | 1 u ≈ a proton; not kilograms |
| Charge (`charge_number`) | elementary charge | integer multiple of *e* |
| RF angular frequency (`omega`) | radian per second | angular, not Hz |
| RF phase (`phase`) | radian | not degrees |

### Naming: Python vs. wire

Field names are snake_case in Python and serialise to camelCase (or a physics
convention) on the wire. `populate_by_name=True` means you can construct the
models with either. Aliases you will meet: `E_nominal`, `dE_fwhm`,
`spaceCharge`, `magneticField`, `mirrorMode`, `V_dc`, `V_rf`, and the coil
fields `R`, `I`, `N`. The examples below use the Python snake_case form.

### Axes, origin, and the bounding box

The geometry builder (`ionforge.geometry.Geometry`) works in absolute
coordinates:

- **z is the optical axis.** `Cylinder` and `Cone` extrude along +z: `geo.add(prim, z=z0)` places the primitive's base at `z = z0` and it extends to `z0 + length`. An `AnnularDisk` lies flat in the plane `z = z0`. A `Sphere` is centred at `z = z0`.
- **x and y are transverse.** Primitives are generated centred on the z axis, so the axis of rotational symmetry passes through `x = y = 0`. For an `axisymmetric` geometry this is the symmetry axis.
- **The origin is fixed at (0, 0, 0).** The builder does **not** recentre or offset geometry to fit the bounding box; you position every primitive explicitly with the `z=` argument, and x/y are centred on the axis by construction.
- **The bounding box is a size-only record.** `Geometry(bounding_box=(sx, sy, sz))` stores a `BoundingBox` holding just the box `size` and a `voltage` (`bounding_box_voltage`, default `0.0` V), which represents the outer domain boundary. The builder applies no translation from it. Choose a box large enough to enclose all your electrodes plus head-room for the fields to decay.

### Symmetry

`SerializedGeometry.symmetry` (set on the geometry, `none` / `axisymmetric` /
`planar`) tells the solver about geometric symmetry: `axisymmetric` means
rotational symmetry about z. Choose a solver consistent with the geometry
(e.g. `bem_axisym` or `fd` for an axisymmetric lens). The separate
`ModelParams.symmetry` block (below) carries an additional mirror-plane hint.

## `solver`: `SolverParams`

Selects the field solver and its discretisation.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `solver_type` | enum (**required**) | - | Which solver to run (see table below). |
| `method` | enum `direct` / `cg` / `sor` | `None` | Linear-solve strategy for the discretised system. `direct` = dense factorisation; `cg` = conjugate gradient (iterative); `sor` = successive over-relaxation. `None` lets the solver pick. Change only if the default is too slow or fails to converge. |
| `resolution` | `Resolution` | `None` | Discretisation knobs (below). `None` uses solver defaults. |

`solver_type` values:

| Value | Solver | Use for |
|---|---|---|
| `fd` | Finite difference, axisymmetric grid | Rotationally symmetric geometries on an (r, z) grid |
| `fd_3d` | Finite difference, 3-D grid | Fully 3-D geometries with no exploitable symmetry |
| `bem_2d` | Boundary element, 2-D | Accepted alias for the axisymmetric boundary-element formulation; use `bem_axisym` for new work |
| `bem_3d` | Boundary element, 3-D | 3-D geometries where a surface method is preferable to a volume grid |
| `bem_axisym` | Boundary element, axisymmetric | Rotationally symmetric lenses (the einzel-lens example uses this) |
| `hybrid` | Combined approach | Setups the platform routes through more than one method |

### `resolution`: `Resolution`

Every field is optional (`None` = solver default). Which knobs apply depends on
`solver_type`; set only the ones relevant to your solver; knobs that do not
apply to the selected solver are ignored.

| Field | Type | Default | Applies to | Meaning |
|---|---|---|---|---|
| `n_segments` | int > 0 | `None` | BEM | Number of boundary segments; higher = finer surface discretisation, more accurate and slower. |
| `quadrature_order` | int > 0 | `None` | BEM | Order of numerical integration over each segment; raise for near-field accuracy. |
| `rtol` | float > 0 | `None` | FD iterative | Relative tolerance for the iterative field solve. |
| `max_iter` | int > 0 | `None` | FD iterative | Cap on solver iterations. |
| `nr` | int > 0 | `None` | axisym grid | Grid points in the radial (r) direction. |
| `nz` | int > 0 | `None` | axisym / 3-D grid | Grid points along z. |
| `nx` | int > 0 | `None` | planar grid | Grid points in x. |
| `ny` | int > 0 | `None` | planar grid | Grid points in y. |
| `z_max` | float (m) | `None` | axisym | Overrides the axisymmetric solve domain extent along z; use to extend the domain past the geometry so fields decay before the boundary. |

Higher grid/segment counts trade runtime for accuracy. Start from defaults and
refine until your figure of merit (transmission, focal length, resolving power)
stops moving.

## `beam`: `BeamParams`

The particle source. A run launches `n_particles` sampled from the nominal
energy and the specified spreads.

| Field | Type | Default | Units | Meaning |
|---|---|---|---|---|
| `position` | list | `[-0.05, 0]` | m | Launch coordinates of the source in the solver's working plane. The default places the source upstream of the geometry. See the note below. |
| `direction` | list | `None` | - | Initial direction vector for the beam. `None` uses the default launch direction (aligned with the propagation axis). |
| `e_nominal` | float ≥ 0 | `50` | eV | Nominal (central) kinetic energy of the beam. |
| `d_e_fwhm` | float ≥ 0 | `0` | eV | Full-width-half-maximum energy spread. `0` = monoenergetic. Set this to model a real source's energy distribution (e.g. for resolving-power studies). |
| `angle_fwhm_deg` | float ≥ 0 | `0` | degree | FWHM angular divergence of the launched rays. `0` = perfectly collimated. |
| `mass_amu` | float > 0 | `1` | u | Particle mass in atomic mass units (`1` ≈ proton / H⁺). |
| `charge_number` | int > 0 | `1` | *e* | Charge as a multiple of the elementary charge. |
| `n_particles` | int > 0 | `100` | - | Number of particles in the ensemble. More particles reduce statistical noise in scored metrics at the cost of runtime. |
| `seed` | int | `42` | - | RNG seed for sampling the energy and angular spreads. A fixed seed makes a run reproducible; vary it to resample the same distribution. |

**Note on `position` / `direction`.** These are 2-element coordinate lists in
the solver's 2-D solve frame rather than full 3-D geometry coordinates. For
the axisymmetric solvers the default `[-0.05, 0]` places the source on the
optical axis, 50 mm upstream. Treat the default as the reference and adjust
relative to it; see also "Where particles are scored" under `ensemble`.

## `integrator`: `IntegratorParams`

Adaptive-step time integration of each trajectory. All times are in **seconds**.

| Field | Type | Default | Units | Meaning |
|---|---|---|---|---|
| `dt_init` | float > 0 | `1e-12` | s | Initial time step. |
| `dt_min` | float > 0 | `1e-16` | s | Smallest step the adaptive controller may take before giving up. |
| `dt_max` | float > 0 | `1e-9` | s | Largest step allowed. |
| `rtol` | float > 0 | `1e-9` | - | Relative error tolerance per step; lower = more accurate, slower. |
| `atol` | float > 0 | `1e-15` | - | Absolute error tolerance per step. |
| `max_steps` | int > 0 | `20000` | - | Cap on integration steps per particle. Raise for long flight paths that hit the cap before reaching the exit plane. |
| `t_max` | float > 0 | `1e-6` | s | Maximum flight time per particle. Raise for slow or long trajectories. |
| `store_every` | int > 0 | `10` | - | Trajectory decimation: store every Nth step. Larger = smaller trajectory output. |
| `use_gpu` | bool | `False` | - | Request GPU integration where available. |

Tighten `rtol`/`atol` and lower `dt_max` if trajectories look noisy or fail
energy conservation; loosen them for speed once results are stable.

## `ensemble`: `EnsembleParams`

Defines where particles terminate and how they are scored.

| Field | Type | Default | Units | Meaning |
|---|---|---|---|---|
| `exit_plane` | enum (**required**) | - | - | Selects the exit-scoring rule (see below). |
| `slit_centre` | float | `None` | m | Centre of a scoring slit at the exit, measured along the scoring line (the optical axis for axisymmetric solvers). `None` = no slit. |
| `slit_half_width` | float | `None` | m | Half-width of the scoring slit. Particles outside the slit are counted as blocked; use with `slit_centre` to model an aperture/detector slit. |
| `store_trajectories` | bool | `False` | - | Persist full trajectories (subject to `store_every`) alongside scored metrics. Enable for visualisation/debugging; leave off for large ensembles. |

**Where particles are scored.** For the axisymmetric solvers a particle is
scored where its ray crosses the optical (z) axis, the natural rule for
focal-length and analyser measurements. The recorded exit position is the
axial coordinate of that crossing, and the slit fields select a window around
it along the axis. For other solver types the scoring plane follows the
solver's 2-D solve frame.

## `space_charge`: `SpaceChargeParams`

Optional iterative, self-consistent space-charge solve: the beam's own charge
density perturbs the field, which is re-solved until convergence. Omit the
block entirely for non-interacting (test-particle) runs.

| Field | Type | Default | Units | Meaning |
|---|---|---|---|---|
| `beam_current` | float > 0 | **required** | A | Total beam current used to weight the charge density. |
| `r_max` | float > 0 | **required** | m | Radial extent of the space-charge grid. |
| `z_min` | float | **required** | m | Lower z bound of the grid. |
| `z_max` | float | **required** | m | Upper z bound of the grid. |
| `nr` | int > 0 | **required** | - | Radial grid resolution. |
| `nz` | int > 0 | **required** | - | Axial grid resolution. |
| `max_iter` | int > 0 | `20` | - | Maximum self-consistent iterations. |
| `tol` | float > 0 | `0.001` | - | Convergence tolerance for the iteration. |

Size the grid (`r_max`, `z_min`, `z_max`) to enclose the beam envelope over the
region where space charge matters. Raise `max_iter` or loosen `tol` if the
solve does not converge.

## `magnetic_field`: `MagneticFieldParams`

Optional static magnetic field, specified as a list of `coils`. Each coil is
one of three types (SI: metres and amperes). `centre` and `axis` are 3-vectors;
`axis` sets the coil's orientation.

| Field | Type | Units | Meaning |
|---|---|---|---|
| `coils` | list | - | One or more coils; the total field is their superposition. |

Common fields on every coil: `centre` (3-vector, m), `axis` (3-vector,
orientation), `R` (float > 0, coil radius in m), `I` (current in A),
`type` (discriminator).

| `type` | Extra fields | Meaning |
|---|---|---|
| `circular_loop` | - | A single circular current loop. |
| `solenoid` | `N` (int > 0, turns), `length` (float > 0, m) | A finite solenoid of `N` turns over `length`. |
| `helmholtz` | `spacing` (float > 0, m) | A Helmholtz pair separated by `spacing`. |

## `symmetry`: mirror hint

A mirror-symmetry hint distinct from the geometry's rotational `symmetry`.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `mirror_mode` | enum `none` / `mirror` / `biaxial` | `none` | Declares a mirror plane (`mirror`) or two orthogonal mirror planes (`biaxial`) the solver may exploit. Set only when the geometry genuinely has that symmetry. |

## `fast_adjust`: `FastAdjust`

Per-electrode voltage overrides applied on top of the geometry's stored
voltages, without re-uploading geometry. Electrodes declared here are also the
ones an RF drive (below) can reference.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `False` | Turn fast-adjust on. |
| `gpu` | bool | `False` | Request GPU-accelerated fast-adjust where available. |
| `electrodes` | list of `Electrode` | `[]` | The electrodes to override / expose (see below). |
| `parent_run_id` | str | `None` | Identifier of a prior run to base the fast-adjust on. |

Each `Electrode`:

| Field | Type | Default | Units | Meaning |
|---|---|---|---|---|
| `name` | str (non-empty) | **required** | - | Electrode name; used to reference it (e.g. from an RF drive). |
| `voltage` | float | **required** | V | Voltage to hold this electrode at. |
| `group` | str | `None` | - | Optional geometry group this electrode maps to. |
| `mask_key` | str | `None` | - | Optional key selecting a solver mask for this electrode. |

## `callbacks`: `Callbacks`

Per-step effects layered onto the integration.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `drag` | `Drag` | `None` | A velocity-dependent drag force. |
| `rf_drives` | list of `RfDrive` | `[]` | Time-varying voltages on named electrodes. |
| `radial_aperture` | `RadialAperture` | `None` | A radial cutoff that removes particles straying too far off-axis. |

### `drag`: `Drag`

| Field | Type | Units | Meaning |
|---|---|---|---|
| `drag_coeff` | float > 0 | - | Drag coefficient. Model a buffer-gas or damping medium; larger = stronger damping. |

### `rf_drives`: `RfDrive`

Applies a sinusoidal voltage to a named electrode:

```
V(t) = V_dc + V_rf · cos(omega · t + phase)
```

| Field | Type | Default | Units | Meaning |
|---|---|---|---|---|
| `electrode` | str (non-empty) | **required** | - | Name of the driven electrode. **It must be declared in `fast_adjust.electrodes`**: a drive referencing an undeclared electrode is rejected when the run starts. |
| `v_dc` (`V_dc`) | float | **required** | V | DC offset of the drive. |
| `v_rf` (`V_rf`) | float | **required** | V | RF amplitude (peak). |
| `omega` | float > 0 | **required** | rad/s | Angular frequency (not Hz: `omega = 2π·f`). |
| `phase` | float | `0` | rad | Phase offset (not degrees). |

Use RF drives for ion traps, quadrupole mass filters, or any time-varying
electrode. Every driven electrode needs a matching entry in
`fast_adjust.electrodes`.

### `radial_aperture`: `RadialAperture`

| Field | Type | Units | Meaning |
|---|---|---|---|
| `r_max` | float > 0 | m | Radial cutoff: particles beyond this radius are removed. |
| `z_min` | float | m | Start of the z range over which the aperture applies. |
| `z_max` | float | m | End of the z range over which the aperture applies. |

## Worked example: an einzel lens

The end-to-end example (`examples/run_simulation.py`) runs a rotationally
symmetric three-tube einzel lens with the axisymmetric boundary-element solver
and a monoenergetic 1 keV proton beam:

```python
from ionforge.client import BeamParams, ModelParams, SolverParams

params = ModelParams(
    solver=SolverParams(solver_type="bem_axisym"),
    beam=BeamParams(
        e_nominal=1000.0,     # nominal beam energy, eV (1 keV)
        mass_amu=1.0,         # proton
        charge_number=1,      # singly charged
        n_particles=200,      # ensemble size
        angle_fwhm_deg=1.0,   # small angular spread, degrees
        seed=42,              # reproducible sampling
    ),
)
```

`bem_axisym` is chosen because the lens is `axisymmetric`. Everything not set
(integrator, ensemble scoring, space charge, magnetic field) falls back to
solver defaults.

Nested blocks that the client does not export as classes (for example
`FastAdjust`, `Callbacks`, `RfDrive`) can be passed as plain dicts, which
`ModelParams` validates. For instance, adding an RF drive:

```python
params = ModelParams(
    solver=SolverParams(solver_type="bem_axisym"),
    beam=BeamParams(e_nominal=1000.0, mass_amu=1.0, charge_number=1),
    fast_adjust={
        "enabled": True,
        "electrodes": [{"name": "tube_centre", "voltage": -2000.0}],
    },
    callbacks={
        "rf_drives": [
            {
                "electrode": "tube_centre",  # declared in fast_adjust.electrodes
                "V_dc": -2000.0,
                "V_rf": 200.0,
                "omega": 6.283e6,            # rad/s
                "phase": 0.0,                # rad
            }
        ]
    },
)
```
