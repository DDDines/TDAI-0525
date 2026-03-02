from __future__ import annotations

"""Add contextual module comments to Frontend source files."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = PROJECT_ROOT / "Frontend" / "app" / "src"

VALID_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {"__tests__", "__mocks__", "dist", "node_modules"}


def _humanize(text: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", " ", text).replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", value).strip().lower()


def _build_comment(path: Path) -> str:
    rel = path.relative_to(FRONTEND_SRC)
    module_name = _humanize(path.stem) or "module"
    feature_scope = _humanize(" ".join(rel.parts[:-1])) or "frontend"
    return (
        "/**\n"
        f" * Module {module_name}.\n"
        " *\n"
        f" * Implements frontend behavior for {feature_scope}.\n"
        " */\n\n"
    )


def _has_module_comment(source: str) -> bool:
    trimmed = source.lstrip()
    return trimmed.startswith("/**")


def main() -> int:
    changed = 0
    for path in FRONTEND_SRC.rglob("*"):
        if path.suffix.lower() not in VALID_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        source = path.read_text(encoding="utf-8")
        if _has_module_comment(source):
            continue

        updated = _build_comment(path) + source
        path.write_text(updated, encoding="utf-8")
        changed += 1

    print(f"updated_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
