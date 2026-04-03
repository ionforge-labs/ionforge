"""Geometry primitives and serialization models.

This subpackage intentionally has no scipy or simulator imports — it is
designed to be Pyodide-safe so the same code can run in the browser
and on the server.
"""

from .builder import Geometry
from .models import (
    BoundingBox,
    Edge,
    Face,
    Group,
    SerializedGeometry,
    Vec3,
    Vertex,
)
from .primitives import AnnularDisk, Cone, Cylinder, Sphere

__all__ = [
    "AnnularDisk",
    "BoundingBox",
    "Cone",
    "Cylinder",
    "Edge",
    "Face",
    "Geometry",
    "Group",
    "SerializedGeometry",
    "Sphere",
    "Vec3",
    "Vertex",
]
