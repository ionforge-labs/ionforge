# List available recipes
default:
    @just --list

# Install dev dependencies
setup:
    uv sync --extra dev

# Run the test suite
test *args:
    uv run pytest {{ args }}

# Run tests with coverage
test-cov:
    uv run pytest --cov

# Run ruff linter
lint:
    uv run ruff check .

# Run ruff linter with auto-fix
lint-fix:
    uv run ruff check . --fix

# Check code formatting
format-check:
    uv run ruff format --check .

# Auto-format code
format:
    uv run ruff format .

# Run type checking
typecheck:
    uv run ty check

# Run all checks (lint, format, typecheck, test)
check: lint format-check typecheck test

# Install git hooks (pre-push)
install-hooks:
    cp scripts/pre-push .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
    @echo "Git hooks installed."

# Run an example script (e.g. just example build_geometry)
example name:
    uv run python examples/{{ name }}.py

# --- Schema (TypeScript) ---

# Install schema package dependencies
schema-setup:
    cd packages/schema && pnpm install

# Generate Zod schemas from Pydantic models
schema-generate:
    uv run python -m ionforge.geometry.export_schema > packages/schema/geometry-schema.json
    cd packages/schema && pnpm run generate

# Build the schema package
schema-build: schema-generate
    cd packages/schema && pnpm run build

# Type-check the schema package
schema-typecheck:
    cd packages/schema && pnpm run typecheck

# Lint and format the schema package
schema-check: schema-generate schema-typecheck
    cd packages/schema && pnpm run check

# Run all checks (Python + schema)
check-all: check schema-check schema-build
