"""Build a simple lens column using parametric primitives."""

from ionforge.geometry import AnnularDisk, Cone, Cylinder, Geometry

geo = Geometry(bounding_box=(0.1, 0.1, 0.3))

# Drift tube
geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube_1"))

# Aperture plate
geo.add(
    AnnularDisk(inner_radius=0.003, outer_radius=0.01, voltage=0, name="aperture"),
    z=0.06,
)

# Tapered section
geo.add(
    Cone(bottom_radius=0.01, top_radius=0.005, length=0.03, voltage=-50, name="taper"),
    z=0.07,
)

# Second tube
geo.add(Cylinder(r=0.005, length=0.05, voltage=100, name="tube_2"), z=0.10)

serialized = geo.to_serialized_geometry()

# Validate
errors = serialized.validate_consistency()
if errors:
    for err in errors:
        print(f"  ERROR: {err}")
else:
    print("Geometry is consistent.")

unassigned = serialized.all_groups_have_voltage()
if unassigned:
    print(f"Groups missing voltage: {unassigned}")
else:
    print("All groups have voltages assigned.")

n_verts = len(serialized.vertices)
n_faces = len(serialized.faces)
n_groups = len(serialized.groups)
print(f"\n{n_verts} vertices, {n_faces} faces, {n_groups} groups")
