from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "Backend"


def _iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if path.is_file():
            yield path


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def test_module_level_legacy_services_use_deprecation_proxy():
    offenders: list[str] = []
    for path in _iter_python_files(BACKEND_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse(path)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if not target.id.endswith("_legacy_service"):
                continue
            if not isinstance(node.value, ast.Call):
                offenders.append(f"{rel}:{node.lineno} -> not a call")
                continue
            func = node.value.func
            if not isinstance(func, ast.Name) or func.id != "deprecated_legacy_service_proxy":
                offenders.append(f"{rel}:{node.lineno} -> {ast.unparse(func)}")

    assert not offenders, (
        "Legacy services must be wrapped by deprecated_legacy_service_proxy:\n"
        + "\n".join(offenders)
    )
