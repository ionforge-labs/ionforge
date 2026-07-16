"""Generate the JSON Schema for SerializedGeometry.

Emits a standard JSON Schema straight from the Pydantic model - useful for
validation or for generating types in other languages:

    uv run python examples/export_schema.py > geometry-schema.json
"""

import json

from ionforge.geometry import SerializedGeometry

schema = SerializedGeometry.model_json_schema()
print(json.dumps(schema, indent=2))
