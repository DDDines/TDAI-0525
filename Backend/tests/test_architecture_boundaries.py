from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ROOT = PROJECT_ROOT / "Backend" / "application"
APPLICATION_SERVICES_ROOT = APPLICATION_ROOT / "services"


def _iter_python_files(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _parse_python_file(path: Path) -> ast.AST:
    source = path.read_text(encoding="utf-8-sig")
    return ast.parse(source, filename=str(path))


def _import_targets(path: Path) -> list[str]:
    tree = _parse_python_file(path)
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                continue
            targets.append(module)
    return targets


def test_application_does_not_import_backend_services_modules():
    offenders: list[str] = []
    for path in _iter_python_files(APPLICATION_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.services" or target.startswith("Backend.services."):
                offenders.append(f"{rel}: {target}")

    assert not offenders, "Unexpected imports to Backend.services:\n" + "\n".join(offenders)


def test_application_does_not_import_backend_router_modules():
    offenders: list[str] = []
    for path in _iter_python_files(APPLICATION_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.routers" or target.startswith("Backend.routers."):
                offenders.append(f"{rel}: {target}")

    assert not offenders, "Unexpected imports to Backend.routers:\n" + "\n".join(offenders)


def test_application_services_do_not_define_dunder_getattr_fallbacks():
    offenders: list[str] = []
    for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "__getattr__":
                offenders.append(f"{rel}:{node.lineno}")

    assert not offenders, "Unexpected __getattr__ fallbacks:\n" + "\n".join(offenders)


def test_application_services_do_not_import_legacy_infrastructure_bridges():
    offenders: list[str] = []
    for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.infrastructure.legacy" or target.startswith(
                "Backend.infrastructure.legacy."
            ):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Unexpected imports to Backend.infrastructure.legacy:\n"
        + "\n".join(offenders)
    )


def test_application_services_do_not_call_private_methods_from_external_objects():
    offenders: list[str] = []
    for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue

            attr_name = node.func.attr
            if not attr_name.startswith("_") or attr_name.startswith("__"):
                continue

            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id in {"self", "cls"}:
                continue

            offenders.append(f"{rel}:{node.lineno} -> {attr_name}")

    assert not offenders, (
        "Unexpected private method calls on non-self objects:\n"
        + "\n".join(offenders)
    )
