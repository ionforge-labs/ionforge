"""Generate the JSON Schema for SerializedGeometry.

This schema can be fed into json-schema-to-zod to generate TypeScript types
that stay in sync with the Python models:

    python examples/export_schema.py > geometry-schema.json
    npx json-schema-to-zod -i geometry-schema.json -o geometry.generated.ts
"""

import json

from ionforge.geometry import SerializedGeometry

schema = SerializedGeometry.model_json_schema()
print(json.dumps(schema, indent=2))
