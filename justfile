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

# --- Client codegen ---

# Generate Pydantic models from an OpenAPI spec
codegen spec:
    uv run datamodel-codegen \
        --input {{ spec }} \
        --input-file-type openapi \
        --output src/ionforge/_types/_generated.py \
        --output-model-type pydantic_v2.BaseModel \
        --base-class ionforge._types._base_model.ApiModel \
        --snake-case-field \
        --use-union-operator \
        --use-standard-collections \
        --target-python-version 3.11 \
        --openapi-scopes schemas paths \
        --use-operation-id-as-name \
        --formatters ruff-format ruff-check
    @echo "Generated src/ionforge/_types/_generated.py"

# Run all checks
check-all: check
