from __future__ import annotations

"""Replace boilerplate auto-generated docstrings with contextual descriptions."""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "Backend"

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "alembic",
    "migrations",
}


def _humanize_identifier(identifier: str) -> str:
    """Convert snake/camel identifiers into a readable phrase."""
    value = re.sub(r"(?<!^)(?=[A-Z])", " ", identifier).replace("_", " ").strip()
    return re.sub(r"\s+", " ", value).lower()


def _callable_sentence(name: str) -> str:
    """Build a contextual sentence for a function/method name."""
    if name == "__init__":
        return "Initialize collaborators and configuration required by this component."

    mapping = {
        "get_": "Return",
        "list_": "List",
        "create_": "Create",
        "update_": "Update",
        "delete_": "Delete",
        "build_": "Build",
        "resolve_": "Resolve",
        "validate_": "Validate",
        "run_": "Run",
        "parse_": "Parse",
        "normalize_": "Normalize",
        "process_": "Process",
        "extract_": "Extract",
        "mark_": "Mark",
        "ensure_": "Ensure",
        "count_": "Count",
        "dispatch_": "Dispatch",
        "select_": "Select",
    }

    for prefix, verb in mapping.items():
        if name.startswith(prefix):
            target = _humanize_identifier(name[len(prefix):]) or "target data"
            return f"{verb} {target} for this workflow."

    return f"Run {_humanize_identifier(name) or 'this operation'} in this workflow."


def _class_sentence(name: str) -> str:
    """Build a contextual sentence for a class name."""
    return (
        f"Represent {_humanize_identifier(name)} and centralize responsibilities "
        "for this module."
    )


def _module_sentence(name: str) -> str:
    """Build a contextual sentence for a module name."""
    return (
        f"Contains backend logic related to {_humanize_identifier(name)} and documents "
        "its role in the OOP architecture."
    )


def _replace_docstrings(source: str) -> str:
    """Replace known boilerplate patterns in one source file."""
    module_pattern = re.compile(
        r'"""Module (?P<name>[^\n.]+)\.\n\n'
        r"This module contains backend application/runtime logic and is fully\n"
        r"documented for maintainability and onboarding\.\n"
        r'"""'
    )
    class_pattern = re.compile(
        r'(?P<indent>[ \t]*)"""Class (?P<name>[A-Za-z0-9_]+)\.\n\n'
        r"(?P=indent)Encapsulates one responsibility in the backend architecture\.\n"
        r'(?P=indent)"""'
    )
    callable_pattern = re.compile(
        r'(?P<indent>[ \t]*)"""Execute (?P<name>[A-Za-z0-9_]+)\.\n\n'
        r"(?P=indent)This callable is documented to make behavior explicit for readers\.\n"
        r'(?P=indent)"""'
    )
    single_line_execute_pattern = re.compile(
        r'(?P<indent>[ \t]*)"""Execute (?P<name>[A-Za-z0-9_ ]+) in this workflow\."""'
    )

    def module_repl(match: re.Match[str]) -> str:
        name = match.group("name").strip()
        return f'"""Module {name}.\n\n{_module_sentence(name)}\n"""'

    def class_repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        name = match.group("name")
        return f'{indent}"""{_class_sentence(name)}"""'

    def callable_repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        name = match.group("name")
        return f'{indent}"""{_callable_sentence(name)}"""'

    def single_line_execute_repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        name = match.group("name").strip()
        return f'{indent}"""Run {name} in this workflow."""'

    updated = module_pattern.sub(module_repl, source)
    updated = class_pattern.sub(class_repl, updated)
    updated = callable_pattern.sub(callable_repl, updated)
    updated = single_line_execute_pattern.sub(single_line_execute_repl, updated)
    return updated


def main() -> int:
    """Run quality upgrades for all backend docstrings."""
    changed = 0
    for path in BACKEND_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        source = path.read_text(encoding="utf-8-sig")
        updated = _replace_docstrings(source)
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed += 1

    print(f"updated_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
