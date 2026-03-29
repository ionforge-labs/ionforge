"""Tests for ionforge.geometry.visualization."""

from __future__ import annotations

import pytest

from ionforge.geometry import AnnularDisk, Cylinder, Geometry
from ionforge.geometry.visualization._common import (
    prepare_mesh,
    resolve_color_by,
    voltage_to_color,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _sample_geometry() -> Geometry:
    """Two-group geometry with distinct voltages."""
    geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
    geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube", n_segments=4))
    geo.add(
        AnnularDisk(
            inner_radius=0.005,
            outer_radius=0.01,
            voltage=-200,
            name="plate",
            n_segments=4,
        ),
        z=0.06,
    )
    return geo


def _geometry_with_none_voltage() -> Geometry:
    """Geometry where one group has voltage=None."""
    geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
    geo.add(Cylinder(r=0.01, length=0.05, voltage=100, name="tube", n_segments=4))
    geo.add(
        AnnularDisk(
            inner_radius=0.005,
            outer_radius=0.01,
            voltage=None,
            name="plate",
            n_segments=4,
        ),
        z=0.06,
    )
    return geo


# ------------------------------------------------------------------
# voltage_to_color
# ------------------------------------------------------------------


class TestVoltageToColor:
    def test_none_is_grey(self) -> None:
        assert voltage_to_color(None, -100, 100) == "#808080"

    def test_zero_is_white_diverging(self) -> None:
        assert voltage_to_color(0.0, -100, 100) == "#ffffff"

    def test_positive_max_is_red(self) -> None:
        c = voltage_to_color(100.0, -100, 100)
        assert c == "#ff0000"

    def test_negative_max_is_blue(self) -> None:
        c = voltage_to_color(-100.0, -100, 100)
        assert c == "#0000ff"

    def test_equal_bounds_returns_white(self) -> None:
        assert voltage_to_color(50.0, 50.0, 50.0) == "#ffffff"

    def test_all_positive_range(self) -> None:
        # vmin=0 vmax=100: voltage=0 → white, voltage=100 → red
        assert voltage_to_color(0.0, 0.0, 100.0) == "#ffffff"
        assert voltage_to_color(100.0, 0.0, 100.0) == "#ff0000"

    def test_all_negative_range(self) -> None:
        # vmin=-100 vmax=0: voltage=-100 → blue, voltage=0 → white
        assert voltage_to_color(-100.0, -100.0, 0.0) == "#0000ff"
        assert voltage_to_color(0.0, -100.0, 0.0) == "#ffffff"


# ------------------------------------------------------------------
# resolve_color_by
# ------------------------------------------------------------------


class TestResolveColorBy:
    def test_explicit_group(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        assert resolve_color_by(sg, "group") == "group"

    def test_explicit_voltage(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        assert resolve_color_by(sg, "voltage") == "voltage"

    def test_auto_all_voltages_set(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        assert resolve_color_by(sg, None) == "voltage"

    def test_auto_some_voltages_none(self) -> None:
        sg = _geometry_with_none_voltage().to_serialized_geometry()
        assert resolve_color_by(sg, None) == "group"

    def test_invalid_raises(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        with pytest.raises(ValueError, match="color_by"):
            resolve_color_by(sg, "invalid")


# ------------------------------------------------------------------
# prepare_mesh
# ------------------------------------------------------------------


class TestPrepareMesh:
    def test_group_coloring(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        pm = prepare_mesh(sg, "group")
        assert len(pm.faces) == len(sg.faces)
        assert len(pm.groups) == 2
        # All faces should use one of the two group colours
        colors = {fd.color for fd in pm.faces}
        group_colors = {g.color for g in pm.groups}
        assert colors <= group_colors

    def test_voltage_coloring(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        pm = prepare_mesh(sg, "voltage")
        # Group with positive voltage → reddish, negative → bluish
        assert pm.groups[0].voltage == 100
        assert pm.groups[1].voltage == -200
        # Colours should differ between the two groups
        assert pm.groups[0].color != pm.groups[1].color

    def test_positions_shape(self) -> None:
        sg = _sample_geometry().to_serialized_geometry()
        pm = prepare_mesh(sg, "group")
        assert pm.positions.shape == (len(sg.vertices), 3)

    def test_empty_geometry(self) -> None:
        geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
        sg = geo.to_serialized_geometry()
        pm = prepare_mesh(sg, "group")
        assert len(pm.faces) == 0
        assert len(pm.groups) == 0


# ------------------------------------------------------------------
# Matplotlib backend
# ------------------------------------------------------------------


class TestMatplotlibBackend:
    def test_renders_without_error(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        geo = _sample_geometry()
        fig = geo.visualize(backend="matplotlib", show=False)
        assert fig is not None
        plt.close(fig)

    def test_color_by_voltage(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        geo = _sample_geometry()
        fig = geo.visualize(backend="matplotlib", color_by="voltage", show=False)
        assert fig is not None
        plt.close(fig)

    def test_empty_geometry(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        geo = Geometry(bounding_box=(0.1, 0.1, 0.2))
        fig = geo.visualize(backend="matplotlib", show=False)
        assert fig is not None
        plt.close(fig)

    def test_with_title(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        geo = _sample_geometry()
        fig = geo.visualize(backend="matplotlib", show=False, title="Test Title")
        assert fig is not None
        plt.close(fig)


# ------------------------------------------------------------------
# Backend dispatch errors
# ------------------------------------------------------------------


class TestBackendErrors:
    def test_unknown_backend_raises(self) -> None:
        geo = _sample_geometry()
        with pytest.raises(ValueError, match="Unknown backend"):
            geo.visualize(backend="nonexistent", show=False)

    def test_invalid_color_by_raises(self) -> None:
        geo = _sample_geometry()
        with pytest.raises(ValueError, match="color_by"):
            geo.visualize(color_by="invalid", show=False)
