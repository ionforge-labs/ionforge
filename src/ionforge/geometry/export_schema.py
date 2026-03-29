"""Export the SerializedGeometry JSON Schema to stdout.

Usage::

    python -m ionforge.geometry.export_schema > geometry-schema.json

The output can be fed into ``json-schema-to-zod`` to generate a Zod
schema that stays in sync with the Python models::

    cd packages/schema && pnpm run generate
"""

import json
import sys

from .models import SerializedGeometry


def main() -> None:
    schema = SerializedGeometry.model_json_schema()
    json.dump(schema, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
