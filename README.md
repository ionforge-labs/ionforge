# IonForge

Open-source charged particle optics toolkit.

The SDK provides Pydantic v2 geometry models for defining simulation meshes, STL mesh import/export with quality metrics, and JSON Schema generation for TypeScript codegen.

## Installation

```bash
uv add ionforge
```

For STL mesh support (adds numpy):

```bash
uv add "ionforge[stl]"
```

## Quick Start

```python
from ionforge.geometry import (
    BoundingBox, Edge, Face, Group, SerializedGeometry, Vertex,
)

geo = SerializedGeometry(
    vertices=[
        Vertex(id="v0", position=(0.0, 0.0, 0.0)),
        Vertex(id="v1", position=(0.1, 0.0, 0.0)),
        Vertex(id="v2", position=(0.05, 0.1, 0.0)),
    ],
    edges=[
        Edge(id="e0", v0="v0", v1="v1", face_ids=["f0"]),
        Edge(id="e1", v0="v1", v1="v2", face_ids=["f0"]),
        Edge(id="e2", v0="v2", v1="v0", face_ids=["f0"]),
    ],
    faces=[
        Face(id="f0", vertex_ids=["v0", "v1", "v2"], edge_ids=["e0", "e1", "e2"]),
    ],
    bounding_box=BoundingBox(size=(0.2, 0.2, 0.2), voltage=0.0),
    groups=[
        Group(id="g0", name="plate", color="#ff0000", voltage=10.0, face_ids=["f0"]),
    ],
    group_order=["g0"],
)

errors = geo.validate_consistency()  # [] if valid
```

## Examples

Runnable scripts are in the [`examples/`](examples/) directory. Run any of them with:

```bash
uv run python examples/<name>.py
```

### Building geometry from scratch

Construct vertices, edges, faces, and groups to define a triangular plate, then validate referential integrity and voltage assignment.

```python
from ionforge.geometry import (
    BoundingBox, Edge, Face, Group, SerializedGeometry, Vertex,
)

vertices = [
    Vertex(id="v0", position=(0.0, 0.0, 0.0)),
    Vertex(id="v1", position=(0.1, 0.0, 0.0)),
    Vertex(id="v2", position=(0.05, 0.1, 0.0)),
]

edges = [
    Edge(id="e0", v0="v0", v1="v1", face_ids=["f0"]),
    Edge(id="e1", v0="v1", v1="v2", face_ids=["f0"]),
    Edge(id="e2", v0="v2", v1="v0", face_ids=["f0"]),
]

faces = [
    Face(id="f0", vertex_ids=["v0", "v1", "v2"], edge_ids=["e0", "e1", "e2"]),
]

groups = [
    Group(id="g0", name="plate", color="#ff0000", voltage=10.0, face_ids=["f0"]),
]

geo = SerializedGeometry(
    vertices=vertices,
    edges=edges,
    faces=faces,
    bounding_box=BoundingBox(size=(0.2, 0.2, 0.2), voltage=0.0),
    groups=groups,
    group_order=["g0"],
)

# Check cross-reference integrity (vertex IDs, face IDs, etc.)
errors = geo.validate_consistency()
assert errors == []

# Check all groups have a voltage assigned
unassigned = geo.all_groups_have_voltage()
assert unassigned == []
```

See [`examples/build_geometry.py`](examples/build_geometry.py) for the full runnable version.

### STL import and export

Load a mesh from an STL file, inspect quality metrics, and re-export. Requires the `[stl]` extra.

```python
from ionforge.geometry.stl_import import load_stl, mesh_stats, write_stl

# Load STL with mm -> metres conversion
triangles = load_stl("model.stl", scale_factor=1e-3)

# Print mesh quality statistics
stats = mesh_stats(triangles, verbose=True)
# Mesh statistics:
#   Triangles: 2  (0 degenerate, 2 valid)
#   Total area: 500.00 mm²
#   Edge range: 0.707 – 1.000 mm
#   Aspect ratio: mean=1.41  max=1.41

# Export as binary STL
write_stl("output.stl", triangles, name="my_mesh")
```

See [`examples/stl_round_trip.py`](examples/stl_round_trip.py) for a self-contained runnable version.

### JSON round-trip

Geometry models use snake_case in Python and camelCase when serialized to JSON, matching the TypeScript frontend. Both naming conventions are accepted when parsing.

```python
import json
from ionforge.geometry import SerializedGeometry

# Serialize to camelCase JSON
camel_json = json.dumps(geo.model_dump(by_alias=True), indent=2)
# {"version": 1, "units": "m", "boundingBox": {...}, "groupOrder": [...], ...}

# Parse from camelCase
parsed = SerializedGeometry.model_validate_json(camel_json)

# Parse from snake_case (also works)
parsed = SerializedGeometry.model_validate({
    "version": 1,
    "units": "m",
    "vertices": [],
    "edges": [],
    "faces": [],
    "bounding_box": {"size": [1, 1, 1], "voltage": 0},
    "groups": [],
    "group_order": [],
})
```

See [`examples/json_round_trip.py`](examples/json_round_trip.py) for the full runnable version.

### JSON Schema generation

Generate a JSON Schema from the Pydantic models, useful for TypeScript codegen with tools like `json-schema-to-zod`:

```bash
python -m ionforge.geometry.export_schema > geometry-schema.json
```

Then generate TypeScript types:

```bash
npx json-schema-to-zod -i geometry-schema.json -o geometry.generated.ts
```

See [`examples/export_schema.py`](examples/export_schema.py) for the programmatic version.

## Development

```bash
uv sync --extra dev --extra stl
uv run pytest
uv run ruff check .
uv run pyright
```
