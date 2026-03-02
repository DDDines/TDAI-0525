from __future__ import annotations

"""Insert missing module/class/function docstrings in Backend Python files."""

import ast
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "Backend"

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "alembic",
    "migrations",
}


@dataclass
class Insertion:
    """Represent a text insertion at a given line in the target file."""

    line_no: int
    text: str


def iter_backend_python_files():
    """Yield Python files under Backend excluding generated/migration areas."""
    for path in BACKEND_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def read_source(path: Path) -> tuple[str, str]:
    """Read file text and detect newline mode."""
    raw = path.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw, newline


def module_docstring_text(path: Path) -> str:
    """Create deterministic module docstring text for one file."""
    module_name = path.stem.replace("_", " ")
    return (
        f'"""Module {module_name}.\n\n'
        "This module contains backend application/runtime logic and is fully\n"
        'documented for maintainability and onboarding.\n"""\n\n'
    )


def class_docstring_text(node_name: str, indent: str) -> str:
    """Build class docstring text."""
    return (
        f'{indent}"""Class {node_name}.\n\n'
        f"{indent}Encapsulates one responsibility in the backend architecture.\n"
        f'{indent}"""\n'
    )


def function_docstring_text(node_name: str, indent: str) -> str:
    """Build function or method docstring text."""
    return (
        f'{indent}"""Execute {node_name}.\n\n'
        f"{indent}This callable is documented to make behavior explicit for readers.\n"
        f'{indent}"""\n'
    )


def module_insert_line(lines: list[str]) -> int:
    """Compute best insertion line for a missing module docstring."""
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1

    if idx < len(lines) and "coding" in lines[idx] and lines[idx].lstrip().startswith("#"):
        idx += 1

    while idx < len(lines) and lines[idx].lstrip().startswith("#"):
        idx += 1

    return idx + 1


def _class_insert_line(node: ast.ClassDef) -> int | None:
    """Resolve safe class docstring insertion line."""
    if not node.body:
        return None
    first_stmt = node.body[0]
    line = first_stmt.lineno
    if isinstance(first_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if first_stmt.decorator_list:
            line = min(line, *(decorator.lineno for decorator in first_stmt.decorator_list))
    return line


def _function_insert_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int | None:
    """Resolve safe function docstring insertion line."""
    if not node.body:
        return None
    first_stmt = node.body[0]
    if (
        isinstance(first_stmt, ast.Expr)
        and isinstance(first_stmt.value, ast.Constant)
        and first_stmt.value.value is Ellipsis
    ):
        # Protocol/interface stubs (`...`) are intentionally skipped.
        return None
    if first_stmt.lineno <= node.lineno:
        # One-line signatures/stubs such as `def f(...): ...`.
        return None
    return first_stmt.lineno


def collect_insertions(source: str, path: Path) -> list[Insertion]:
    """Collect docstring insertions required for one file."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    insertions: list[Insertion] = []

    if ast.get_docstring(tree) is None:
        insertions.append(
            Insertion(
                line_no=module_insert_line(lines),
                text=module_docstring_text(path),
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if ast.get_docstring(node) is not None:
                continue
            insert_line = _class_insert_line(node)
            if insert_line is None:
                continue
            indent = " " * (node.col_offset + 4)
            insertions.append(
                Insertion(
                    line_no=insert_line,
                    text=class_docstring_text(node.name, indent),
                )
            )
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(node) is not None:
                continue
            insert_line = _function_insert_line(node)
            if insert_line is None:
                continue
            indent = " " * (node.col_offset + 4)
            insertions.append(
                Insertion(
                    line_no=insert_line,
                    text=function_docstring_text(node.name, indent),
                )
            )

    return insertions


def apply_insertions(source: str, insertions: list[Insertion]) -> str:
    """Apply insertions to source from bottom to top."""
    if not insertions:
        return source

    lines = source.splitlines(keepends=True)
    for insertion in sorted(insertions, key=lambda x: x.line_no, reverse=True):
        lines.insert(insertion.line_no - 1, insertion.text)
    return "".join(lines)


def main() -> int:
    """Run docstring insertion for all Backend Python files."""
    updated = 0
    parse_errors: list[str] = []

    for path in iter_backend_python_files():
        try:
            source, newline = read_source(path)
            insertions = collect_insertions(source, path)
            if not insertions:
                continue

            new_source = apply_insertions(source, insertions)
            if new_source != source:
                path.write_text(new_source.replace("\n", newline), encoding="utf-8")
                updated += 1
        except SyntaxError:
            parse_errors.append(str(path.relative_to(PROJECT_ROOT)))

    print(f"Updated files: {updated}")
    if parse_errors:
        print("Syntax errors (skipped):")
        for item in parse_errors:
            print(f" - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
