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
