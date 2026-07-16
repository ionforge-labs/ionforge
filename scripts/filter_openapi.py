"""Filter an IonForge OpenAPI spec down to the core resources the SDK covers.

The published Python SDK exposes the core charged particle optics resources:
projects, geometries, models, runs, sweeps, and upload presigning. The upstream
spec also documents surfaces that are not part of the SDK's remit (interactive
notebooks, workspace administration, and other product-only endpoints); this
script keeps only the core paths and prunes any component schemas that are no
longer referenced, so the generated types stay small and focused.

Usage::

    python scripts/filter_openapi.py <input-spec.json> <output-spec.json>
"""

from __future__ import annotations

import json
import sys
from typing import Any

# Exact paths the SDK covers.
ALLOWED_PATHS: frozenset[str] = frozenset(
    {
        "/projects",
        "/projects/{id}",
        "/geometries",
        "/geometries/{id}",
        "/models",
        "/models/{id}",
        "/models/clone",
        "/models/templates",
        "/models/{modelId}/runs",
        "/models/{modelId}/sweeps",
        "/uploads/presign",
    }
)

# Path prefixes the SDK covers in full (runs and sweeps sub-resources).
ALLOWED_PREFIXES: tuple[str, ...] = ("/runs", "/sweeps")


def _is_allowed(path: str) -> bool:
    return path in ALLOWED_PATHS or path.startswith(ALLOWED_PREFIXES)


# HTTP methods that carry operations (as opposed to shared parameters, etc.).
_HTTP_METHODS: frozenset[str] = frozenset(
    {"get", "put", "post", "delete", "patch", "options", "head", "trace"}
)


def _strip_error_responses(path_item: dict[str, Any]) -> dict[str, Any]:
    """Drop non-success responses so generated types stay focused.

    The SDK surfaces HTTP errors through its own typed exception hierarchy, so
    the shared error-envelope schemas do not need to be generated. Keeping only
    2xx responses leaves the models describing request bodies and successful
    payloads, which is all the client consumes.
    """
    result = dict(path_item)
    for method, operation in path_item.items():
        if method not in _HTTP_METHODS or not isinstance(operation, dict):
            continue
        responses = operation.get("responses")
        if not isinstance(responses, dict):
            continue
        kept = {
            code: body for code, body in responses.items() if str(code).startswith("2")
        }
        result[method] = {**operation, "responses": kept}
    return result


def _iter_refs(node: Any) -> list[str]:
    """Collect every local schema ``$ref`` name reachable from *node*."""
    refs: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                prefix = "#/components/schemas/"
                if value.startswith(prefix):
                    refs.append(value[len(prefix) :])
            else:
                refs.extend(_iter_refs(value))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_iter_refs(item))
    return refs


def _reachable_schemas(seeds: set[str], schemas: dict[str, Any]) -> set[str]:
    """Transitively resolve schema references starting from *seeds*."""
    reachable: set[str] = set()
    stack = list(seeds)
    while stack:
        name = stack.pop()
        if name in reachable or name not in schemas:
            continue
        reachable.add(name)
        stack.extend(_iter_refs(schemas[name]))
    return reachable


def filter_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *spec* limited to the SDK's core resources."""
    paths = {
        path: _strip_error_responses(item)
        for path, item in spec.get("paths", {}).items()
        if _is_allowed(path)
    }

    schemas = spec.get("components", {}).get("schemas", {})
    seeds = set(_iter_refs(paths))
    kept = _reachable_schemas(seeds, schemas)

    filtered = dict(spec)
    filtered["paths"] = paths
    if "components" in filtered:
        components = dict(filtered["components"])
        components["schemas"] = {
            name: schema for name, schema in schemas.items() if name in kept
        }
        filtered["components"] = components
    return filtered


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: python scripts/filter_openapi.py <input.json> <output.json>",
            file=sys.stderr,
        )
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    filtered = filter_spec(spec)
    with open(argv[2], "w", encoding="utf-8") as fh:
        json.dump(filtered, fh, indent=2)
    kept_paths = len(filtered["paths"])
    kept_schemas = len(filtered.get("components", {}).get("schemas", {}))
    print(f"Filtered spec: {kept_paths} paths, {kept_schemas} schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
