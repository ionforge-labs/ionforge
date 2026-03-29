#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCHEMA_DIR="$REPO_ROOT/packages/schema"

SCHEMA_FILE="$SCHEMA_DIR/geometry-schema.json"

echo "==> Exporting JSON Schema from Pydantic models..."
uv run --project "$REPO_ROOT" python -m ionforge.geometry.export_schema > "$SCHEMA_FILE"

echo "==> Generating Zod schemas from JSON Schema..."
node "$SCHEMA_DIR/scripts/generate.cjs"

echo "==> Cleaning up intermediate schema..."
rm -f "$SCHEMA_FILE"

echo "Done."
