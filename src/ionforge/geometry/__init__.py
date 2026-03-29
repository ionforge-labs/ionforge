"""Geometry primitives and serialization models.

This subpackage intentionally has no scipy or simulator imports — it is
designed to be Pyodide-safe so the same code can run in the browser
(parametric geometry editor) and on the server (Batch converter).
"""

from .models import (
    BoundingBox,
    Edge,
    Face,
    Group,
    SerializedGeometry,
    Vec3,
    Vertex,
)

__all__ = [
    "BoundingBox",
    "Edge",
    "Face",
    "Group",
    "SerializedGeometry",
    "Vec3",
    "Vertex",
]
