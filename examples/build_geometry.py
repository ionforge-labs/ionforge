"""Build a simple triangular plate geometry from scratch and validate it."""

from ionforge.geometry import (
    BoundingBox,
    Edge,
    Face,
    Group,
    SerializedGeometry,
    Vertex,
)

# Three vertices forming a triangle (positions in metres)
vertices = [
    Vertex(id="v0", position=(0.0, 0.0, 0.0)),
    Vertex(id="v1", position=(0.1, 0.0, 0.0)),
    Vertex(id="v2", position=(0.05, 0.1, 0.0)),
]

# Edges connecting the vertices
edges = [
    Edge(id="e0", v0="v0", v1="v1", face_ids=["f0"]),
    Edge(id="e1", v0="v1", v1="v2", face_ids=["f0"]),
    Edge(id="e2", v0="v2", v1="v0", face_ids=["f0"]),
]

# A single triangular face
faces = [
    Face(id="f0", vertex_ids=["v0", "v1", "v2"], edge_ids=["e0", "e1", "e2"]),
]

# Group the face and assign a voltage
groups = [
    Group(
        id="g0",
        name="plate",
        color="#ff0000",
        voltage=10.0,
        face_ids=["f0"],
    ),
]

# Bounding box defines the simulation domain
bounding_box = BoundingBox(size=(0.2, 0.2, 0.2), voltage=0.0)

geo = SerializedGeometry(
    vertices=vertices,
    edges=edges,
    faces=faces,
    bounding_box=bounding_box,
    groups=groups,
    group_order=["g0"],
)

# Validate referential integrity
errors = geo.validate_consistency()
if errors:
    for err in errors:
        print(f"  ERROR: {err}")
else:
    print("Geometry is consistent.")

# Check all groups have voltages assigned
unassigned = geo.all_groups_have_voltage()
if unassigned:
    print(f"Groups missing voltage: {unassigned}")
else:
    print("All groups have voltages assigned.")
