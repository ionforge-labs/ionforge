"""Tests for geometry primitives and the Geometry builder."""

from ionforge.geometry import (
    AnnularDisk,
    Cone,
    Cylinder,
    Geometry,
    Sphere,
)


class TestCylinder:
    def test_mesh_generates_expected_counts(self):
        c = Cylinder(r=0.01, length=0.05, n_segments=8)
        mesh = c.mesh("cyl", z_offset=0.0)
        assert len(mesh.vertices) == 16  # 8 bottom + 8 top
        assert len(mesh.faces) == 16  # 2 triangles per quad * 8 segments

    def test_mesh_vertices_at_correct_z(self):
        c = Cylinder(r=0.01, length=0.05, n_segments=4)
        mesh = c.mesh("cyl", z_offset=0.1)
        zs = {round(v.position[2], 6) for v in mesh.vertices}
        assert zs == {0.1, 0.15}

    def test_consistency(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.1))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=100, n_segments=8))
        sg = geo.to_serialized_geometry()
        assert sg.validate_consistency() == []


class TestAnnularDisk:
    def test_mesh_generates_expected_counts(self):
        d = AnnularDisk(inner_radius=0.005, outer_radius=0.01, n_segments=8)
        mesh = d.mesh("disk", z_offset=0.0)
        assert len(mesh.vertices) == 16  # 8 inner + 8 outer
        assert len(mesh.faces) == 16

    def test_all_vertices_at_same_z(self):
        d = AnnularDisk(inner_radius=0.005, outer_radius=0.01, n_segments=4)
        mesh = d.mesh("disk", z_offset=0.5)
        zs = {v.position[2] for v in mesh.vertices}
        assert zs == {0.5}

    def test_consistency(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.1))
        geo.add(
            AnnularDisk(inner_radius=0.005, outer_radius=0.01, voltage=0, n_segments=8)
        )
        sg = geo.to_serialized_geometry()
        assert sg.validate_consistency() == []


class TestCone:
    def test_tapered_mesh_counts(self):
        c = Cone(bottom_radius=0.01, top_radius=0.005, length=0.05, n_segments=8)
        mesh = c.mesh("cone", z_offset=0.0)
        assert len(mesh.vertices) == 16
        assert len(mesh.faces) == 16

    def test_pointed_cone_top(self):
        c = Cone(bottom_radius=0.01, top_radius=0.0, length=0.05, n_segments=8)
        mesh = c.mesh("cone", z_offset=0.0)
        assert len(mesh.vertices) == 9  # 8 ring + 1 tip
        assert len(mesh.faces) == 8  # fan of 8 triangles

    def test_pointed_cone_bottom(self):
        c = Cone(bottom_radius=0.0, top_radius=0.01, length=0.05, n_segments=8)
        mesh = c.mesh("cone", z_offset=0.0)
        assert len(mesh.vertices) == 9
        assert len(mesh.faces) == 8

    def test_consistency(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.1))
        geo.add(
            Cone(
                bottom_radius=0.01,
                top_radius=0.005,
                length=0.05,
                voltage=50,
                n_segments=8,
            )
        )
        sg = geo.to_serialized_geometry()
        assert sg.validate_consistency() == []


class TestSphere:
    def test_mesh_has_poles(self):
        s = Sphere(r=0.01, n_segments=8, n_rings=4)
        mesh = s.mesh("sph", z_offset=0.0)
        ids = {v.id for v in mesh.vertices}
        assert "sph_south" in ids
        assert "sph_north" in ids

    def test_mesh_vertex_count(self):
        s = Sphere(r=0.01, n_segments=8, n_rings=4)
        mesh = s.mesh("sph", z_offset=0.0)
        # 2 poles + (n_rings-1) * n_segments interior vertices
        assert len(mesh.vertices) == 2 + 3 * 8

    def test_mesh_face_count(self):
        s = Sphere(r=0.01, n_segments=8, n_rings=4)
        mesh = s.mesh("sph", z_offset=0.0)
        # 2 pole fans of 8 + 2 middle bands of 16
        assert len(mesh.faces) == 8 + 16 + 16 + 8

    def test_consistency(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.1))
        geo.add(Sphere(r=0.01, voltage=0, n_segments=8, n_rings=4))
        sg = geo.to_serialized_geometry()
        assert sg.validate_consistency() == []


class TestGeometryBuilder:
    def test_single_primitive(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.1))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube", n_segments=8))
        sg = geo.to_serialized_geometry()
        assert len(sg.groups) == 1
        assert sg.groups[0].name == "tube"
        assert sg.groups[0].voltage == 100
        assert sg.validate_consistency() == []

    def test_multiple_primitives(self):
        geo = Geometry(bounding_box=(0.2, 0.2, 0.3))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube_1", n_segments=8))
        geo.add(
            AnnularDisk(
                inner_radius=0.005,
                outer_radius=0.01,
                voltage=0,
                name="aperture",
                n_segments=8,
            ),
            z=0.06,
        )
        geo.add(
            Cylinder(r=0.01, length=0.05, voltage=50, name="tube_2", n_segments=8),
            z=0.07,
        )
        sg = geo.to_serialized_geometry()
        assert len(sg.groups) == 3
        assert sg.groups[0].name == "tube_1"
        assert sg.groups[1].name == "aperture"
        assert sg.groups[2].name == "tube_2"
        assert sg.validate_consistency() == []

    def test_duplicate_names_get_suffixed(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube", n_segments=4))
        geo.add(
            Cylinder(r=0.01, length=0.05, voltage=50, name="tube", n_segments=4), z=0.06
        )
        sg = geo.to_serialized_geometry()
        names = [g.name for g in sg.groups]
        assert names == ["tube_1", "tube_2"]

    def test_bounding_box_voltage(self):
        geo = Geometry(bounding_box=(1.0, 1.0, 1.0), bounding_box_voltage=5.0)
        geo.add(Cylinder(r=0.01, length=0.05, voltage=0, n_segments=4))
        sg = geo.to_serialized_geometry()
        assert sg.bounding_box.voltage == 5.0

    def test_no_faces_shared_between_groups(self):
        geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=100, n_segments=8))
        geo.add(Cylinder(r=0.01, length=0.05, voltage=50, n_segments=8), z=0.06)
        sg = geo.to_serialized_geometry()
        all_face_ids = []
        for g in sg.groups:
            all_face_ids.extend(g.face_ids)
        assert len(all_face_ids) == len(set(all_face_ids))
