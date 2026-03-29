#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SDK_DIR="$REPO_ROOT/packages/sdk"

SCHEMA_FILE="$SDK_DIR/geometry-schema.json"

echo "==> Exporting JSON Schema from Pydantic models..."
uv run --project "$REPO_ROOT" python -m ionforge.geometry.export_schema > "$SCHEMA_FILE"

echo "==> Generating Zod schemas from JSON Schema..."
node "$SDK_DIR/scripts/generate.cjs"

echo "==> Cleaning up intermediate schema..."
rm -f "$SCHEMA_FILE"

echo "Done."
