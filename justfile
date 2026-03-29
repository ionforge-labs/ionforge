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

# Run an example script (e.g. just example build_geometry)
example name:
    uv run python examples/{{ name }}.py

# --- SDK (TypeScript) ---

# Install SDK dependencies
sdk-setup:
    cd packages/sdk && pnpm install

# Generate Zod schemas from Pydantic models
sdk-generate:
    cd packages/sdk && pnpm run generate

# Build the SDK package
sdk-build: sdk-generate
    cd packages/sdk && pnpm run build

# Type-check the SDK
sdk-typecheck:
    cd packages/sdk && pnpm run typecheck

# Lint and format the SDK
sdk-check: sdk-generate sdk-typecheck
    cd packages/sdk && pnpm run check

# Run all checks (Python + SDK)
check-all: check sdk-check sdk-build
