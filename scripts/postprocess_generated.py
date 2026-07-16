"""Post-process ``datamodel-code-generator`` output.

The generator emits enum-typed model fields with plain *string* defaults, e.g.::

    symmetry: Symmetry | None = "none"

Because ``StrEnum`` members are strings at runtime the generated module imports
and runs correctly, but a static type checker rejects the bare ``"none"`` as a
value of type ``Symmetry``. This script rewrites each such default to reference
the matching enum member (``Symmetry.none``) so the generated models type-check
cleanly. It only touches defaults whose declared field type is a ``StrEnum``
defined in the same module and whose string value is one of that enum's members,
so it is safe to run unconditionally as part of ``just codegen`` and is
idempotent.

After rewriting, the script re-parses its own output and fails loud (non-zero
exit, listing offenders) if any ``StrEnum``-annotated field still carries a
plain-string default, so a missed rewrite can never slip through silently.

Usage::

    python scripts/postprocess_generated.py <generated-module.py>
"""

from __future__ import annotations

import ast
import sys


def _is_strenum_base(base: ast.expr) -> bool:
    """True if *base* names ``StrEnum`` as a bare name or an attribute.

    Accepts both the ``StrEnum`` name (``from enum import StrEnum``) and the
    ``enum.StrEnum`` attribute form, so a change in how the generator imports
    the base class does not silently disable the rewrite.
    """
    if isinstance(base, ast.Name):
        return base.id == "StrEnum"
    if isinstance(base, ast.Attribute):
        return base.attr == "StrEnum"
    return False


def _enum_value_to_member(tree: ast.Module) -> dict[str, dict[str, str]]:
    """Map each ``StrEnum`` class to its ``{value: member_name}`` lookup."""
    enums: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_is_strenum_base(b) for b in node.bases):
            continue
        members: dict[str, str] = {}
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                members[stmt.value.value] = stmt.targets[0].id
        enums[node.name] = members
    return enums


def _referenced_enum(annotation: ast.expr, enum_names: set[str]) -> str | None:
    """Return the single enum name referenced by *annotation*, if exactly one."""
    found = {
        n.id
        for n in ast.walk(annotation)
        if isinstance(n, ast.Name) and n.id in enum_names
    }
    return next(iter(found)) if len(found) == 1 else None


def _string_enum_defaults(source: str) -> list[str]:
    """Describe every ``StrEnum``-annotated field left with a plain-string default.

    After :func:`postprocess` runs, any such field is a *missed* rewrite: either
    its declared enum has no matching member, or the emission slipped past the
    detection heuristics. Each entry is a human-readable ``Class.field`` locator.
    """
    tree = ast.parse(source)
    enum_names = set(_enum_value_to_member(tree))
    remaining: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign) or stmt.value is None:
                continue
            if not isinstance(stmt.value, ast.Constant):
                continue
            if not isinstance(stmt.value.value, str):
                continue
            if _referenced_enum(stmt.annotation, enum_names) is None:
                continue
            field = stmt.target.id if isinstance(stmt.target, ast.Name) else "<field>"
            remaining.append(
                f"{node.name}.{field} (line {stmt.lineno}): {stmt.value.value!r}"
            )
    return remaining


def _replacements(source: str) -> list[tuple[int, int, str]]:
    """Collect ``(start, end, text)`` byte-offset edits for enum defaults."""
    if not source.isascii():
        raise ValueError(
            "source contains non-ASCII characters; ast col_offset is a byte "
            "offset, so char-based slicing would corrupt the rewrite. Refusing "
            "to edit rather than emit garbage."
        )
    tree = ast.parse(source)
    enums = _enum_value_to_member(tree)
    enum_names = set(enums)
    lines = source.splitlines(keepends=True)
    line_starts = [0]
    for line in lines:
        line_starts.append(line_starts[-1] + len(line))

    def offset(lineno: int, col: int) -> int:
        return line_starts[lineno - 1] + col

    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign) or stmt.value is None:
                continue
            default = stmt.value
            if not isinstance(default, ast.Constant):
                continue
            if not isinstance(default.value, str):
                continue
            enum_name = _referenced_enum(stmt.annotation, enum_names)
            if enum_name is None:
                continue
            member = enums[enum_name].get(default.value)
            if member is None:
                continue
            start = offset(default.lineno, default.col_offset)
            end = offset(default.end_lineno, default.end_col_offset)
            edits.append((start, end, f"{enum_name}.{member}"))
    return edits


def postprocess(source: str) -> str:
    """Return *source* with enum-typed string defaults rewritten to members."""
    edits = _replacements(source)
    for start, end, text in sorted(edits, reverse=True):
        source = source[:start] + text + source[end:]
    return source


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: python scripts/postprocess_generated.py <generated-module.py>",
            file=sys.stderr,
        )
        return 2
    path = argv[1]
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    updated = postprocess(source)
    remaining = _string_enum_defaults(updated)
    if remaining:
        print(
            "error: StrEnum-annotated fields still have plain-string defaults "
            "after rewrite (missed rewrites):",
            file=sys.stderr,
        )
        for entry in remaining:
            print(f"  {entry}", file=sys.stderr)
        return 1
    if updated != source:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
