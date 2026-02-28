from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "Backend"
APPLICATION_ROOT = PROJECT_ROOT / "Backend" / "application"
APPLICATION_SERVICES_ROOT = APPLICATION_ROOT / "services"
ROUTERS_ROOT = PROJECT_ROOT / "Backend" / "routers"
INFRASTRUCTURE_ADAPTERS_ROOT = PROJECT_ROOT / "Backend" / "infrastructure" / "adapters"
INFRASTRUCTURE_RUNTIME_ROOT = PROJECT_ROOT / "Backend" / "infrastructure" / "runtime"
INFRASTRUCTURE_RUNTIME_SERVICES_ROOT = (
    PROJECT_ROOT / "Backend" / "infrastructure" / "runtime_services"
)
INFRASTRUCTURE_RUNTIME_MODULES_ROOT = (
    PROJECT_ROOT / "Backend" / "infrastructure" / "runtime_modules"
)
BACKEND_TESTS_ROOT = PROJECT_ROOT / "Backend" / "tests"
PROJECT_TESTS_ROOT = PROJECT_ROOT / "tests"
CRUD_MODULE_FILES = sorted(BACKEND_ROOT.glob("crud_*.py"))


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


def test_infrastructure_adapters_do_not_import_backend_services_modules():
    offenders: list[str] = []
    for path in _iter_python_files(INFRASTRUCTURE_ADAPTERS_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.services" or target.startswith("Backend.services."):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Unexpected direct imports to Backend.services in infrastructure adapters:\n"
        + "\n".join(offenders)
    )


def test_infrastructure_runtime_providers_do_not_import_backend_services_modules():
    offenders: list[str] = []
    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.services" or target.startswith("Backend.services."):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Unexpected direct imports to Backend.services in infrastructure runtime providers:\n"
        + "\n".join(offenders)
    )


def test_infrastructure_runtime_providers_do_not_import_runtime_modules_directly():
    offenders: list[str] = []
    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.infrastructure.runtime_modules" or target.startswith(
                "Backend.infrastructure.runtime_modules."
            ):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Runtime providers must depend on runtime_services, not runtime_modules:\n"
        + "\n".join(offenders)
    )


def test_runtime_modules_imports_are_constrained_to_runtime_services_and_tests():
    offenders: list[str] = []

    allowed_prefixes = [
        INFRASTRUCTURE_RUNTIME_SERVICES_ROOT.resolve(),
        BACKEND_TESTS_ROOT.resolve(),
        (BACKEND_ROOT / "testing").resolve(),
    ]

    for path in _iter_python_files(BACKEND_ROOT):
        resolved = path.resolve()
        rel = path.relative_to(PROJECT_ROOT)

        if str(resolved).startswith(str(INFRASTRUCTURE_RUNTIME_MODULES_ROOT.resolve())):
            continue
        if any(str(resolved).startswith(str(prefix)) for prefix in allowed_prefixes):
            continue

        for target in _import_targets(path):
            if target == "Backend.infrastructure.runtime_modules" or target.startswith(
                "Backend.infrastructure.runtime_modules."
            ):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Direct runtime_modules imports are only allowed in runtime_services and tests:\n"
        + "\n".join(offenders)
    )


def test_backend_tests_do_not_import_runtime_modules_directly():
    offenders: list[str] = []

    for path in _iter_python_files(BACKEND_TESTS_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.infrastructure.runtime_modules" or target.startswith(
                "Backend.infrastructure.runtime_modules."
            ):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Backend/tests must consume runtime_services or Backend.testing.runtime_apis, "
        "not import runtime_modules directly:\n" + "\n".join(offenders)
    )


def test_project_tests_do_not_import_runtime_modules_directly():
    offenders: list[str] = []

    for path in _iter_python_files(PROJECT_TESTS_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.infrastructure.runtime_modules" or target.startswith(
                "Backend.infrastructure.runtime_modules."
            ):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "tests/ must consume application/runtime_services surfaces, "
        "not import runtime_modules directly:\n" + "\n".join(offenders)
    )


def test_infrastructure_runtime_providers_expose_get_runtime_service_only():
    offenders: list[str] = []
    missing: list[str] = []

    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_ROOT):
        if path.name == "__init__.py":
            continue

        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }

        if "get_runtime_module" in function_names:
            offenders.append(f"{rel}: get_runtime_module")
        if "get_runtime_service" not in function_names:
            missing.append(str(rel))

    assert not offenders, (
        "Legacy runtime provider entrypoints are not allowed:\n" + "\n".join(offenders)
    )
    assert not missing, (
        "Runtime providers must expose get_runtime_service():\n"
        + "\n".join(missing)
    )


def test_runtime_services_do_not_import_backend_services_modules():
    offenders: list[str] = []
    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_SERVICES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.services" or target.startswith("Backend.services."):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Unexpected imports to Backend.services in infrastructure runtime services:\n"
        + "\n".join(offenders)
    )


def test_runtime_services_do_not_call_runtime_module_functions_directly():
    offenders: list[str] = []
    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_SERVICES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            if not isinstance(owner, ast.Name):
                continue
            if not owner.id.endswith("_module"):
                continue
            if node.func.attr.startswith("get_"):
                continue
            offenders.append(f"{rel}:{node.lineno} -> {owner.id}.{node.func.attr}")

    assert not offenders, (
        "Runtime services must consume workflow/service objects, "
        "not call runtime module function APIs directly:\n" + "\n".join(offenders)
    )


def test_backend_code_does_not_import_backend_services_modules():
    offenders: list[str] = []

    for path in _iter_python_files(BACKEND_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.services" or target.startswith("Backend.services."):
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Unexpected imports to Backend.services in Backend package:\n"
        + "\n".join(offenders)
    )


def test_runtime_modules_do_not_import_backend_crud_package_root():
    offenders: list[str] = []
    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "Backend.crud":
                        offenders.append(f"{rel}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                module = node.module or ""
                if module == "Backend":
                    for alias in node.names:
                        if alias.name == "crud" or alias.name.startswith("crud_"):
                            offenders.append(f"{rel}: from Backend import {alias.name}")
                elif module == "Backend.crud":
                    offenders.append(f"{rel}: {module}")

    assert not offenders, (
        "Runtime modules must depend on CRUD workflows, not Backend crud package root/module functions:\n"
        + "\n".join(offenders)
    )


def test_runtime_modules_do_not_expose_public_function_wrappers():
    offenders: list[str] = []
    allowed_non_get_public_functions = {
        "create_web_extraction_enrichment_workflow",
        "apply_web_data_extractor_runtime_state",
        "reset_web_data_extractor_runtime_state",
    }

    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            function_name = node.name
            if function_name.startswith("_"):
                continue
            if function_name.startswith("get_"):
                continue
            if function_name in allowed_non_get_public_functions:
                continue
            offenders.append(f"{rel}:{node.lineno} -> {function_name}")

    assert not offenders, (
        "Runtime modules must expose workflow/factory entrypoints only "
        "(no public procedural wrappers):\n" + "\n".join(offenders)
    )


def test_crud_modules_do_not_expose_public_function_wrappers():
    offenders: list[str] = []
    for path in CRUD_MODULE_FILES:
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            function_name = node.name
            if function_name.startswith("_"):
                continue
            if function_name.startswith("get_") and function_name.endswith("_workflow"):
                continue
            offenders.append(f"{rel}:{node.lineno} -> {function_name}")

    assert not offenders, (
        "CRUD modules must expose workflow getter entrypoints only "
        "(no public procedural wrappers):\n" + "\n".join(offenders)
    )


def test_runtime_modules_do_not_instantiate_singletons_at_module_scope():
    offenders: list[str] = []
    allowed_runtime_module_callees = {"ThreadPoolExecutor"}

    for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            if not isinstance(node.value.func, ast.Name):
                continue
            callee = node.value.func.id
            if callee in allowed_runtime_module_callees:
                continue
            if (
                (callee.startswith("_") and len(callee) > 1 and callee[1].isupper())
                or callee[:1].isupper()
            ):
                offenders.append(f"{rel}:{node.lineno} -> {callee}")

    assert not offenders, (
        "Runtime modules must not keep class singletons at module scope:\n"
        + "\n".join(offenders)
    )


def test_crud_modules_do_not_instantiate_singletons_at_module_scope():
    offenders: list[str] = []

    for path in CRUD_MODULE_FILES:
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            if not isinstance(node.value.func, ast.Name):
                continue
            callee = node.value.func.id
            if (
                (callee.startswith("_") and len(callee) > 1 and callee[1].isupper())
                or callee[:1].isupper()
            ):
                offenders.append(f"{rel}:{node.lineno} -> {callee}")

    assert not offenders, (
        "CRUD modules must not keep class singletons at module scope:\n"
        + "\n".join(offenders)
    )


def test_routers_do_not_import_backend_crud_modules_directly():
    offenders: list[str] = []
    for path in _iter_python_files(ROUTERS_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "Backend.crud" or alias.name.startswith("Backend.crud_"):
                        offenders.append(f"{rel}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    continue

                if module == "Backend":
                    for alias in node.names:
                        if alias.name == "crud" or alias.name.startswith("crud_"):
                            offenders.append(f"{rel}: from Backend import {alias.name}")
                elif module == "Backend.crud" or module.startswith("Backend.crud_"):
                    offenders.append(f"{rel}: {module}")

    assert not offenders, (
        "Routers must consume application/infrastructure services, not Backend crud modules:\n"
        + "\n".join(offenders)
    )


def test_routers_do_not_import_application_services_package_root():
    offenders: list[str] = []
    for path in _iter_python_files(ROUTERS_ROOT):
        rel = path.relative_to(PROJECT_ROOT)
        for target in _import_targets(path):
            if target == "Backend.application.services":
                offenders.append(f"{rel}: {target}")

    assert not offenders, (
        "Routers must import explicit service modules, not Backend.application.services package root:\n"
        + "\n".join(offenders)
    )


def test_backend_crud_imports_are_constrained_to_runtime_and_data_access_layers():
    offenders: list[str] = []

    allowed_files = {
        (APPLICATION_SERVICES_ROOT / "data_access_service.py").resolve(),
    }
    allowed_prefixes = [
        INFRASTRUCTURE_RUNTIME_MODULES_ROOT.resolve(),
    ]

    for path in _iter_python_files(BACKEND_ROOT):
        resolved = path.resolve()
        rel = path.relative_to(PROJECT_ROOT)

        if rel.parts[:2] in {("Backend", "tests"), ("Backend", "testing")}:
            continue

        if resolved in allowed_files:
            continue
        if any(str(resolved).startswith(str(prefix)) for prefix in allowed_prefixes):
            continue

        tree = _parse_python_file(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "Backend.crud" or alias.name.startswith("Backend.crud_"):
                        offenders.append(f"{rel}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                module = node.module or ""
                if module == "Backend":
                    for alias in node.names:
                        if alias.name == "crud" or alias.name.startswith("crud_"):
                            offenders.append(f"{rel}: from Backend import {alias.name}")
                elif module == "Backend.crud" or module.startswith("Backend.crud_"):
                    offenders.append(f"{rel}: {module}")

    assert not offenders, (
        "Backend crud imports are only allowed in runtime_modules and data_access_service:\n"
        + "\n".join(offenders)
    )


def test_tests_do_not_import_backend_crud_modules_directly():
    offenders: list[str] = []

    for root in (BACKEND_TESTS_ROOT, PROJECT_TESTS_ROOT):
        if not root.exists():
            continue

        for path in _iter_python_files(root):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "Backend.crud":
                            offenders.append(f"{rel}: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue
                    module = node.module or ""
                    if module == "Backend":
                        for alias in node.names:
                            if alias.name == "crud" or alias.name.startswith("crud_"):
                                offenders.append(f"{rel}: from Backend import {alias.name}")
                    elif module == "Backend.crud":
                        offenders.append(f"{rel}: {module}")

    assert not offenders, (
        "Tests must not import legacy Backend.crud package root or root aliases:\n"
        + "\n".join(offenders)
    )


def test_data_access_service_uses_workflow_instances_for_crud_calls():
    data_access_path = APPLICATION_SERVICES_ROOT / "data_access_service.py"
    tree = _parse_python_file(data_access_path)
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if not isinstance(owner, ast.Name):
            continue
        if owner.id.startswith("crud") and owner.id != "crud":
            offenders.append(f"{data_access_path.relative_to(PROJECT_ROOT)}:{node.lineno}")

    assert not offenders, (
        "data_access_service must delegate through workflow instances, "
        "not module-level crud function calls:\n" + "\n".join(offenders)
    )


def test_application_services_package_init_has_no_eager_reexports():
    init_path = APPLICATION_SERVICES_ROOT / "__init__.py"
    tree = _parse_python_file(init_path)
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            offenders.append(f"{init_path.relative_to(PROJECT_ROOT)}:{node.lineno}")

    assert not offenders, (
        "Backend.application.services.__init__ must not perform eager imports:\n"
        + "\n".join(offenders)
    )


def test_tests_do_not_import_private_backend_symbols():
    offenders: list[str] = []

    for root in (BACKEND_TESTS_ROOT, PROJECT_TESTS_ROOT):
        if not root.exists():
            continue

        for path in _iter_python_files(root):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level:
                    continue
                module = node.module or ""
                if not module.startswith("Backend."):
                    continue
                for alias in node.names:
                    if alias.name.startswith("_"):
                        offenders.append(f"{rel}:{node.lineno} -> {module}.{alias.name}")

    assert not offenders, (
        "Tests must use public Backend symbols, not private names prefixed with '_':\n"
        + "\n".join(offenders)
    )
