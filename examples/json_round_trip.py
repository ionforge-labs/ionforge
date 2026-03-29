"""Serialize geometry to JSON (camelCase) and parse it back."""

import json

from ionforge.geometry import (
    BoundingBox,
    Edge,
    Face,
    Group,
    SerializedGeometry,
    Vertex,
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

# Serialize to camelCase JSON (matches the TypeScript frontend)
camel_json = json.dumps(geo.model_dump(by_alias=True), indent=2)
print("camelCase JSON output:")
print(camel_json)

# Parse it back
parsed = SerializedGeometry.model_validate_json(camel_json)
print(f"\nRound-tripped: {len(parsed.vertices)} vertices, {len(parsed.faces)} faces")

# snake_case input also works
snake_data = {
    "version": 1,
    "units": "m",
    "vertices": [{"id": "v0", "position": [0, 0, 0]}],
    "edges": [],
    "faces": [],
    "bounding_box": {"size": [1, 1, 1], "voltage": 0},
    "groups": [],
    "group_order": [],
}
parsed_snake = SerializedGeometry.model_validate(snake_data)
print(f"\nParsed from snake_case: version={parsed_snake.version}")
