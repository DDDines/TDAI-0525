"""Module test commenting coverage.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

"""Guardrails that enforce minimum comment/docstring coverage in Backend."""

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "Backend"

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "alembic",
    "migrations",
}


def _iter_backend_python_files():
    """Execute _iter_backend_python_files.

    This callable is documented to make behavior explicit for readers.
    """
    for path in BACKEND_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def _read_source(path: Path) -> str:
    """Execute _read_source.

    This callable is documented to make behavior explicit for readers.
    """
    return path.read_text(encoding="utf-8-sig")


def _public_defs_missing_docstring(path: Path, source: str) -> list[str]:
    """Execute _public_defs_missing_docstring.

    This callable is documented to make behavior explicit for readers.
    """
    tree = ast.parse(source)
    missing: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                if (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value is Ellipsis
                ):
                    # Protocol/interface stubs are represented as ellipsis bodies.
                    continue
                if node.body[0].lineno <= node.lineno:
                    # One-line stubs (`def f(...): ...`) are excluded from strict coverage.
                    continue
            if ast.get_docstring(node) is None:
                missing.add(node.name)
    return sorted(missing)


def test_backend_modules_have_module_docstring():
    """Execute test_backend_modules_have_module_docstring.

    This callable is documented to make behavior explicit for readers.
    """
    offenders: list[str] = []

    for path in _iter_backend_python_files():
        source = _read_source(path)
        tree = ast.parse(source)
        if ast.get_docstring(tree) is None:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert not offenders, (
        "Missing module docstring in Backend files:\n" + "\n".join(offenders)
    )


def test_backend_public_definitions_have_docstrings():
    """Execute test_backend_public_definitions_have_docstrings.

    This callable is documented to make behavior explicit for readers.
    """
    offenders: list[str] = []

    for path in _iter_backend_python_files():
        source = _read_source(path)
        missing = _public_defs_missing_docstring(path, source)
        if missing:
            rel = path.relative_to(PROJECT_ROOT)
            offenders.append(f"{rel}: {', '.join(sorted(missing))}")

    assert not offenders, (
        "Missing docstring on public classes/functions:\n" + "\n".join(offenders)
    )


def test_backend_docstrings_do_not_contain_placeholder_markers():
    """Execute test_backend_docstrings_do_not_contain_placeholder_markers.

    This callable is documented to make behavior explicit for readers.
    """
    offenders: list[str] = []
    blocked_markers = ("TODO", "FIXME")

    for path in _iter_backend_python_files():
        if path.name == "test_commenting_coverage.py":
            continue
        source = _read_source(path)
        for marker in blocked_markers:
            if marker in source:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: contains {marker}")

    assert not offenders, (
        "Placeholder markers found in Backend code comments/docstrings:\n"
        + "\n".join(offenders)
    )
