# AGENTS.md

Guidance for AI coding assistants (and humans) working in the IonForge SDK.
Everything here is grounded in this repository. Prefer running the commands
below over guessing.

## What this is

IonForge is an open-source charged particle optics toolkit. The SDK lets you:

- build simulation geometry from parametric primitives,
- import/export STL meshes with quality metrics,
- serialize geometry to/from JSON (Pydantic v2 models), and
- drive simulations on the IonForge cloud API through a typed client.

## Setup and commands

Python 3.11+. Package manager is `uv`; task runner is `just`.

```bash
uv sync --extra dev        # install with dev dependencies
just check                 # lint + format-check + typecheck + test
just test                  # run the test suite (pytest)
just test tests/foo.py     # pass args through to pytest
just example build_geometry  # run examples/build_geometry.py
just codegen <openapi.json>  # regenerate the API client models (see below)
```

Individual checks: `just lint` (ruff), `just format-check`, `just format`,
`just typecheck` (ty).

### Package extras

- `client` — the cloud API client (adds `httpx`).
- `pandas` — DataFrame accessors for sweep/run results (adds `pandas`).
- `viz-plotly` / `viz-pyvista` — one visualization backend each.
- `viz` — all visualization backends (matplotlib + plotly + pyvista).

Matplotlib visualization needs no extra when installed via `dev`; for a plain
install, use one of the `viz*` extras.

## Conventions

- **Units are SI**: metres, volts, seconds. Beam energies are in eV (not
  joules). Full field-by-field reference in `docs/parameters.md`.
- **z is the optical axis.** `Cylinder` and `Cone` extrude along +z;
  `geo.add(prim, z=z0)` places the base at `z = z0`. `AnnularDisk` lies flat at
  `z = z0`; `Sphere` is centred at `z = z0`.
- **x/y are transverse**, centred on the z axis by construction.
- **Absolute coordinates.** The builder does not recentre or auto-fit geometry;
  position every primitive explicitly. Origin is fixed at `(0, 0, 0)`.
- **The builder requires a domain box.** `bounding_box` is mandatory:
  `Geometry(bounding_box=(sx, sy, sz), symmetry=...)`. `symmetry` is one of
  `none`, `axisymmetric`, `planar`.
- **Style**: ruff with line-length 88 and double quotes; `ty` for type
  checking; pytest tests are plain `test_*` functions (no classes required).

## Package map

No top-level `ionforge` import surface — it is a namespace package. Import from
the subpackages:

- `ionforge.geometry` — `Geometry` builder (`add`, `to_serialized_geometry`,
  and `SerializedGeometry.validate_consistency()` on the result); primitives
  `Cylinder`, `AnnularDisk`, `Cone`, `Sphere`; serialization models `SerializedGeometry`,
  `BoundingBox`, `Vertex`, `Edge`, `Face`, `Group`, `Symmetry`, `Vec3`; STL I/O
  in `ionforge.geometry.stl_import` (`load_stl`, `mesh_stats`, `write_stl`);
  3-D rendering in `ionforge.geometry.visualization` (`render`, or
  `geo.visualize(...)`).
- `ionforge.client` — `IonForge` and `AsyncIonForge` clients. Resources:
  `projects`, `geometries`, `models`, `runs`, `sweeps`, `uploads`. Convenience
  methods: `upload_geometry`, `run_simulation`, `run_sweep`,
  `download_results`. Supports run/sweep polling and result pagination. Typed
  exceptions (`APIError`, `AuthenticationError`, `NotFoundError`, ...).
  Tabular analysis via the `pandas` extra: `sweeps.list_results(...)` returns a
  `SweepResults` collection with `.to_dataframe()` (one row per point, swept
  params as dot-path columns), and `runs.to_dataframe(...)` lists runs.
- `ionforge._types._generated` — request/response and parameter models
  (`ModelParams`, `BeamParams`, `SolverParams`, `IntegratorParams`, ...)
  generated from the public OpenAPI spec. Regenerate with
  `just codegen <spec>`; do not hand-edit this file.

## Pointers

- `README.md` — quickstart and worked snippets for every feature.
- `docs/parameters.md` — full simulation parameter reference (types, defaults,
  units, physical meaning).
- `examples/` — each runnable via `just example <name>`:
  - `build_geometry` — assemble a lens column from primitives.
  - `stl_round_trip` — load an STL, inspect mesh quality, re-export.
  - `json_round_trip` — serialize geometry to/from JSON.
  - `export_schema` — emit the JSON Schema for `SerializedGeometry`.
  - `visualize_geometry` — CLI viewer with `--backend`/`--color-by`.
  - `viz_matplotlib` / `viz_plotly` / `viz_pyvista` — one backend each.
  - `run_simulation` — end-to-end: build, upload, run, download results.

## Common pitfalls

- There is no top-level `ionforge` import surface. Import from
  `ionforge.geometry` / `ionforge.client`, not `import ionforge`.
- The client needs the `client` extra and an API key: set `IONFORGE_API_KEY`
  (or pass `api_key=`). Optionally override the endpoint with `IONFORGE_BASE_URL`.
- The DataFrame accessors (`to_dataframe`) need the `pandas` extra; without it
  they raise `ImportError` naming `ionforge[pandas]`. pandas is imported lazily,
  so the client itself never requires it.
- `ionforge/_types/_generated.py` is generated. Change the codegen inputs and
  rerun `just codegen`, never edit the file directly.
- `Cylinder` has no end caps (it is an open lateral surface). Add `AnnularDisk`
  plates to cap the ends if a solid boundary is needed.
- Mark rotationally symmetric geometries `symmetry="axisymmetric"` and pair
  them with an axisymmetric solver (`bem_axisym` or `fd`).
