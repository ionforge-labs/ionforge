"""Tests for the ``scripts/postprocess_generated.py`` codegen post-processor.

The script rewrites ``StrEnum``-typed string defaults emitted by
``datamodel-code-generator`` into enum-member references. These tests load it
directly from the ``scripts/`` directory (it is not an installed package) and
exercise it over small in-memory source snippets and a temp file.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "postprocess_generated.py"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_postprocess_generated", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pp = _load()


def test_rewrites_string_default_to_enum_member() -> None:
    source = (
        "from enum import StrEnum\n\n\n"
        "class Symmetry(StrEnum):\n"
        '    none = "none"\n'
        '    planar = "planar"\n\n\n'
        "class Model:\n"
        '    symmetry: Symmetry | None = "none"\n'
    )
    updated = pp.postprocess(source)
    assert "symmetry: Symmetry | None = Symmetry.none" in updated
    assert 'symmetry: Symmetry | None = "none"' not in updated


def test_idempotent() -> None:
    source = (
        "from enum import StrEnum\n\n\n"
        "class Symmetry(StrEnum):\n"
        '    none = "none"\n\n\n'
        "class Model:\n"
        '    symmetry: Symmetry | None = "none"\n'
    )
    once = pp.postprocess(source)
    twice = pp.postprocess(once)
    assert once == twice
    # A second pass finds nothing left to rewrite.
    assert pp._string_enum_defaults(once) == []


def test_non_identifier_enum_values_use_member_name() -> None:
    # The value is not a valid identifier, so member name != value; the rewrite
    # must reference the member name, never the raw string value.
    source = (
        "from enum import StrEnum\n\n\n"
        "class Mode(StrEnum):\n"
        '    run_only = "run-only"\n\n\n'
        "class Model:\n"
        '    mode: Mode | None = "run-only"\n'
    )
    updated = pp.postprocess(source)
    assert "mode: Mode | None = Mode.run_only" in updated
    assert '"run-only"' not in updated.splitlines()[-1]


def test_accepts_enum_strenum_attribute_base() -> None:
    source = (
        "import enum\n\n\n"
        "class Symmetry(enum.StrEnum):\n"
        '    none = "none"\n\n\n'
        "class Model:\n"
        '    symmetry: Symmetry | None = "none"\n'
    )
    updated = pp.postprocess(source)
    assert "symmetry: Symmetry | None = Symmetry.none" in updated


def test_non_ascii_source_fails_loud() -> None:
    source = (
        "from enum import StrEnum\n\n\n"
        "# énum comment with non-ascii\n"
        "class Symmetry(StrEnum):\n"
        '    none = "none"\n'
    )
    with pytest.raises(ValueError, match="non-ASCII"):
        pp.postprocess(source)


def test_missed_default_detection_exits_nonzero(tmp_path: Path) -> None:
    # "unknown" is not a member of Symmetry, so it can never be rewritten; the
    # script must exit non-zero and leave the file untouched.
    source = (
        "from enum import StrEnum\n\n\n"
        "class Symmetry(StrEnum):\n"
        '    none = "none"\n\n\n'
        "class Model:\n"
        '    symmetry: Symmetry | None = "unknown"\n'
    )
    path = tmp_path / "gen.py"
    path.write_text(source, encoding="utf-8")

    rc = pp.main(["postprocess_generated.py", str(path)])
    assert rc == 1
    # The offending file is not overwritten when the check fails.
    assert path.read_text(encoding="utf-8") == source


def test_main_rewrites_file_in_place(tmp_path: Path) -> None:
    source = (
        "from enum import StrEnum\n\n\n"
        "class Symmetry(StrEnum):\n"
        '    none = "none"\n\n\n'
        "class Model:\n"
        '    symmetry: Symmetry | None = "none"\n'
    )
    path = tmp_path / "gen.py"
    path.write_text(source, encoding="utf-8")

    rc = pp.main(["postprocess_generated.py", str(path)])
    assert rc == 0
    assert "= Symmetry.none" in path.read_text(encoding="utf-8")
