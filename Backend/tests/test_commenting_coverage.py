"""Architecture guardrails for backend documentation quality."""

from __future__ import annotations

import ast
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "Backend"

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "alembic",
    "migrations",
    "tests",
}

GENERIC_DOCSTRING_PATTERNS = (
    re.compile(r"^Process\s", re.IGNORECASE),
    re.compile(
        r"^Initialize required dependencies and runtime configuration\.?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^Defines the module responsibilities and how it fits in the backend architecture\.?$",
        re.IGNORECASE,
    ),
    re.compile(r"^Select plan\.?$", re.IGNORECASE),
    re.compile(r"^Dispatch or run\.?$", re.IGNORECASE),
    re.compile(r"^Run direct\.?$", re.IGNORECASE),
)


def _iter_backend_python_files():
    """Iterate backend Python files excluding generated and migration folders."""
    for path in BACKEND_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def _read_source(path: Path) -> str:
    """Load source code using UTF-8 (with optional BOM)."""
    return path.read_text(encoding="utf-8-sig")


def _public_defs_missing_docstring(source: str) -> list[str]:
    """Return public classes/functions that still do not define docstrings."""
    tree = ast.parse(source)
    missing: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first_stmt = node.body[0]
            if (
                isinstance(first_stmt, ast.Expr)
                and isinstance(first_stmt.value, ast.Constant)
                and first_stmt.value.value is Ellipsis
            ):
                # Protocol/interface signatures written as stubs do not need body docstrings.
                continue
            if first_stmt.lineno <= node.lineno:
                # Single-line stubs like `def f(...): ...` are excluded.
                continue

        if ast.get_docstring(node) is None:
            missing.add(node.name)

    return sorted(missing)


def _generic_docstring_offenders() -> list[tuple[str, int, str]]:
    """Return generic/placeholder-like docstrings that should be gradually eliminated."""
    offenders: list[tuple[str, int, str]] = []

    for path in _iter_backend_python_files():
        source = _read_source(path)
        tree = ast.parse(source)
        rel = str(path.relative_to(PROJECT_ROOT))

        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            docstring = ast.get_docstring(node)
            if not docstring:
                continue

            normalized = " ".join(docstring.strip().split())
            if any(pattern.match(normalized) for pattern in GENERIC_DOCSTRING_PATTERNS):
                line = getattr(node, "lineno", 1)
                offenders.append((rel, line, normalized))

    return offenders


def test_backend_modules_have_module_docstring():
    """Every backend module must include a module-level docstring."""
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
    """Public API symbols must describe their behavior in docstrings."""
    offenders: list[str] = []

    for path in _iter_backend_python_files():
        source = _read_source(path)
        missing = _public_defs_missing_docstring(source)
        if missing:
            rel = path.relative_to(PROJECT_ROOT)
            offenders.append(f"{rel}: {', '.join(missing)}")

    assert not offenders, (
        "Missing docstring on public classes/functions:\n" + "\n".join(offenders)
    )


def test_backend_docstrings_do_not_contain_placeholder_markers():
    """Comments and docstrings must not keep unresolved placeholder markers."""
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


def test_backend_docstrings_do_not_use_generic_boilerplate():
    """Documentation must be contextual, not generic auto-generated filler text."""
    offenders: list[str] = []
    blocked_fragments = (
        " in this workflow.",
        " for this workflow.",
        "Initialize collaborators and configuration required by this component.",
        "and centralize responsibilities for this module.",
        "This callable is documented to make behavior explicit for readers.",
        "Encapsulates one responsibility in the backend architecture.",
        "This module contains backend application/runtime logic and is fully",
    )

    for path in _iter_backend_python_files():
        if path.name == "test_commenting_coverage.py":
            continue
        source = _read_source(path)
        for fragment in blocked_fragments:
            if fragment in source:
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)}: contains generic fragment `{fragment}`"
                )

    assert not offenders, (
        "Generic docstring boilerplate found in Backend code:\n"
        + "\n".join(offenders)
    )


def test_backend_generic_docstring_count_does_not_regress():
    """Keep reducing generic docstrings and block any regression in total count."""
    offenders = _generic_docstring_offenders()
    max_allowed = 668

    assert len(offenders) <= max_allowed, (
        "Generic docstring count regressed. "
        f"Current={len(offenders)} exceeds allowed={max_allowed}.\n"
        "Sample offenders:\n"
        + "\n".join(f"{path}:{line} -> {doc}" for path, line, doc in offenders[:40])
    )
