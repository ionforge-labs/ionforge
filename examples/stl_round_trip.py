"""Load an STL file, inspect mesh quality, and re-export it.

Creates a small ASCII STL in a temp file so the example is self-contained.
Requires the [stl] extra: uv add "ionforge[stl]"
"""

import tempfile
from pathlib import Path

from ionforge.geometry.stl_import import load_stl, mesh_stats, write_stl

# A minimal ASCII STL with two triangles forming a square
ASCII_STL = """\
solid square
  facet normal 0 0 1
    outer loop
      vertex 0.0 0.0 0.0
      vertex 1.0 0.0 0.0
      vertex 1.0 1.0 0.0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0.0 0.0 0.0
      vertex 1.0 1.0 0.0
      vertex 0.0 1.0 0.0
    endloop
  endfacet
endsolid square
"""

with tempfile.TemporaryDirectory() as tmp:
    input_path = Path(tmp) / "square.stl"
    input_path.write_text(ASCII_STL)

    # Load with mm -> m conversion
    triangles = load_stl(str(input_path), scale_factor=1e-3)
    print(f"Loaded {len(triangles)} triangles\n")

    # Inspect mesh quality
    stats = mesh_stats(triangles, verbose=True)

    # Re-export as binary STL
    output_path = Path(tmp) / "square_out.stl"
    write_stl(str(output_path), triangles, name="square_export")
    print(f"\nWrote {output_path.stat().st_size} bytes to binary STL")
