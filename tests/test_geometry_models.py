"""Tests for ionforge.geometry.models Pydantic definitions."""

import json

import pytest
from pydantic import ValidationError

from ionforge.geometry.models import (
    SerializedGeometry,
)


def _valid_geometry(**overrides: object) -> dict:
    """Minimal valid SerializedGeometry dict (camelCase keys)."""
    base: dict = {
        "version": 1,
        "units": "m",
        "vertices": [
            {"id": "v0", "position": [0.0, 0.0, 0.0]},
            {"id": "v1", "position": [0.1, 0.0, 0.0]},
            {"id": "v2", "position": [0.05, 0.1, 0.0]},
        ],
        "edges": [
            {"id": "e0", "v0": "v0", "v1": "v1", "faceIds": ["f0"]},
            {"id": "e1", "v0": "v1", "v1": "v2", "faceIds": ["f0"]},
            {"id": "e2", "v0": "v2", "v1": "v0", "faceIds": ["f0"]},
        ],
        "faces": [
            {
                "id": "f0",
                "vertexIds": ["v0", "v1", "v2"],
                "edgeIds": ["e0", "e1", "e2"],
            },
        ],
        "boundingBox": {"size": [0.2, 0.2, 0.2], "voltage": 0.0},
        "groups": [
            {
                "id": "g0",
                "name": "plate",
                "color": "#ff0000",
                "voltage": 10.0,
                "faceIds": ["f0"],
            },
        ],
        "groupOrder": ["g0"],
    }
    base.update(overrides)
    return base


class TestModelParsing:
    def test_parse_valid_camel_case(self):
        geo = SerializedGeometry.model_validate(_valid_geometry())
        assert geo.version == 1
        assert len(geo.vertices) == 3
        assert geo.vertices[0].position == [0.0, 0.0, 0.0]
        assert geo.edges[0].face_ids == ["f0"]
        assert geo.bounding_box.voltage == 0.0
        assert geo.groups[0].voltage == 10.0

    def test_parse_snake_case_also_works(self):
        data = {
            "version": 1,
            "units": "m",
            "vertices": [
                {"id": "v0", "position": [0.0, 0.0, 0.0]},
                {"id": "v1", "position": [1.0, 0.0, 0.0]},
                {"id": "v2", "position": [0.0, 1.0, 0.0]},
            ],
            "edges": [
                {"id": "e0", "v0": "v0", "v1": "v1", "face_ids": ["f0"]},
                {"id": "e1", "v0": "v1", "v1": "v2", "face_ids": ["f0"]},
                {"id": "e2", "v0": "v2", "v1": "v0", "face_ids": ["f0"]},
            ],
            "faces": [
                {
                    "id": "f0",
                    "vertex_ids": ["v0", "v1", "v2"],
                    "edge_ids": ["e0", "e1", "e2"],
                },
            ],
            "bounding_box": {"size": [1.0, 1.0, 1.0], "voltage": 0.0},
            "groups": [
                {
                    "id": "g0",
                    "name": "test",
                    "color": "#000",
                    "voltage": 5.0,
                    "face_ids": ["f0"],
                },
            ],
            "group_order": ["g0"],
        }
        geo = SerializedGeometry.model_validate(data)
        assert len(geo.faces) == 1

    def test_dump_uses_camel_case(self):
        geo = SerializedGeometry.model_validate(_valid_geometry())
        d = geo.model_dump(by_alias=True)
        assert "boundingBox" in d
        assert "groupOrder" in d
        assert "faceIds" in d["edges"][0]
        assert "vertexIds" in d["faces"][0]

    def test_null_voltage_allowed(self):
        data = _valid_geometry()
        data["groups"][0]["voltage"] = None
        geo = SerializedGeometry.model_validate(data)
        assert geo.groups[0].voltage is None

    def test_face_needs_2_vertices(self):
        data = _valid_geometry()
        data["faces"][0]["vertexIds"] = ["v0"]
        with pytest.raises(ValidationError):
            SerializedGeometry.model_validate(data)

    def test_invalid_version_rejected(self):
        data = _valid_geometry()
        data["version"] = 2
        with pytest.raises(ValidationError):
            SerializedGeometry.model_validate(data)


class TestConsistencyValidation:
    def test_valid_geometry_no_errors(self):
        geo = SerializedGeometry.model_validate(_valid_geometry())
        assert geo.validate_consistency() == []

    def test_bad_vertex_ref_in_edge(self):
        data = _valid_geometry()
        data["edges"][0]["v0"] = "nonexistent"
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("nonexistent" in e for e in errors)

    def test_bad_face_ref_in_group(self):
        data = _valid_geometry()
        data["groups"][0]["faceIds"] = ["no_such_face"]
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("no_such_face" in e for e in errors)

    def test_duplicate_face_in_groups(self):
        data = _valid_geometry()
        data["groups"].append(
            {
                "id": "g1",
                "name": "other",
                "color": "#00f",
                "voltage": 5.0,
                "faceIds": ["f0"],
            }
        )
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("belongs to both" in e for e in errors)

    def test_unassigned_voltages(self):
        data = _valid_geometry()
        data["groups"][0]["voltage"] = None
        geo = SerializedGeometry.model_validate(data)
        names = geo.all_groups_have_voltage()
        assert "plate" in names

    def test_bad_face_ref_in_edge(self):
        data = _valid_geometry()
        data["edges"][0]["faceIds"] = ["no_such_face"]
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("no_such_face" in e for e in errors)

    def test_group_order_references_nonexistent_group(self):
        data = _valid_geometry()
        data["groupOrder"] = ["g0", "g_nonexistent"]
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("g_nonexistent" in e for e in errors)

    def test_empty_geometry_with_nonempty_group_order(self):
        data = _valid_geometry(
            vertices=[],
            edges=[],
            faces=[],
            groups=[],
            groupOrder=["g_phantom"],
        )
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("g_phantom" in e for e in errors)


class TestEdgeIds:
    def test_group_with_edge_ids_parses(self):
        data = _valid_geometry()
        data["groups"][0]["edgeIds"] = ["e0", "e1"]
        geo = SerializedGeometry.model_validate(data)
        assert geo.groups[0].edge_ids == ["e0", "e1"]

    def test_group_without_edge_ids_defaults_to_empty(self):
        data = _valid_geometry()
        # No edgeIds field at all — should default to []
        geo = SerializedGeometry.model_validate(data)
        assert geo.groups[0].edge_ids == []

    def test_validate_consistency_catches_invalid_edge_ids(self):
        data = _valid_geometry()
        data["groups"][0]["edgeIds"] = ["e-nonexistent"]
        geo = SerializedGeometry.model_validate(data)
        errors = geo.validate_consistency()
        assert any("e-nonexistent" in e for e in errors)

    def test_validate_consistency_passes_with_valid_edge_ids(self):
        data = _valid_geometry()
        data["groups"][0]["edgeIds"] = ["e0", "e1"]
        geo = SerializedGeometry.model_validate(data)
        assert geo.validate_consistency() == []

    def test_dump_includes_edge_ids(self):
        data = _valid_geometry()
        data["groups"][0]["edgeIds"] = ["e0"]
        geo = SerializedGeometry.model_validate(data)
        d = geo.model_dump(by_alias=True)
        assert "edgeIds" in d["groups"][0]
        assert d["groups"][0]["edgeIds"] == ["e0"]


class TestJsonSchemaExport:
    def test_schema_is_valid_json(self):
        schema = SerializedGeometry.model_json_schema()
        text = json.dumps(schema)
        parsed = json.loads(text)
        assert "$defs" in parsed or "properties" in parsed

    def test_schema_has_required_fields(self):
        schema = SerializedGeometry.model_json_schema()
        props = schema.get("properties", {})
        assert "vertices" in props
        assert "edges" in props
        assert "faces" in props
        assert "boundingBox" in props or "bounding_box" in props
        assert "groups" in props
