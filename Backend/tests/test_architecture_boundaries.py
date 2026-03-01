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


class _TopLevelFunctionSurface:

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

    def _is_http_endpoint_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
                "trace",
                "websocket",
            }:
                continue
            owner = decorator.func.value
            if isinstance(owner, ast.Name) and owner.id in {"router", "app"}:
                return True
        return False

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
            INFRASTRUCTURE_ADAPTERS_ROOT.resolve(),
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
            exported_names: set[str] = set()
    
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    exported_names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            exported_names.add(target.id)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    exported_names.add(node.target.id)
    
            if "get_runtime_module" in exported_names:
                offenders.append(f"{rel}: get_runtime_module")
            if "get_runtime_service" not in exported_names:
                missing.append(str(rel))
    
        assert not offenders, (
            "Legacy runtime provider entrypoints are not allowed:\n" + "\n".join(offenders)
        )
        assert not missing, (
            "Runtime providers must expose get_runtime_service():\n"
            + "\n".join(missing)
        )

    def test_backend_top_level_non_endpoint_functions_are_allowlisted():
        offenders: list[str] = []
        allowed_functions = {
            ("Backend/database.py", "get_db"),
        }
    
        for path in _iter_python_files(BACKEND_ROOT):
            if path.is_relative_to(BACKEND_TESTS_ROOT):
                continue
    
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            tree = _parse_python_file(path)
    
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if _is_http_endpoint_function(node):
                    continue
                if (rel, node.name) in allowed_functions:
                    continue

                offenders.append(f"{rel}:{node.lineno} -> {node.name}")
    
        assert not offenders, (
            "Top-level non-endpoint functions are forbidden (use class methods + exported aliases):\n"
            + "\n".join(offenders)
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
                # Allow explicit class construction from runtime modules.
                if node.func.attr[:1].isupper():
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
        allowed_public_functions: set[str] = set()
    
        for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                function_name = node.name
                if function_name.startswith("_"):
                    continue
                if function_name in allowed_public_functions:
                    continue
                offenders.append(f"{rel}:{node.lineno} -> {function_name}")
    
        assert not offenders, (
            "Runtime modules must not expose public function wrappers "
            "(use classes/workflows only):\n" + "\n".join(offenders)
        )

    def test_runtime_modules_do_not_define_top_level_functions():
        offenders: list[str] = []
    
        for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    offenders.append(f"{rel}:{node.lineno} -> {node.name}")
    
        assert not offenders, (
            "Runtime modules must contain only class-based surfaces (no top-level functions):\n"
            + "\n".join(offenders)
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

    def test_runtime_services_do_not_instantiate_singletons_at_module_scope():
        offenders: list[str] = []
    
        for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_SERVICES_ROOT):
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
            "Runtime services must not keep class singletons at module scope:\n"
            + "\n".join(offenders)
        )

    def test_backend_code_does_not_define_module_level_class_singletons():
        offenders: list[str] = []
        allowed_callees = {
            "APIRouter",
            "OAuth2PasswordBearer",
            "OAuth",
            "FastAPI",
            "FileHandler",
            "Formatter",
            "CryptContext",
            "TypeAdapter",
        }
    
        for path in _iter_python_files(BACKEND_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
    
            if rel.parts[:2] in {("Backend", "tests"), ("Backend", "testing")}:
                continue
    
            tree = _parse_python_file(path)
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                if not isinstance(node.value, ast.Call):
                    continue
                if not isinstance(node.value.func, ast.Name):
                    continue
    
                callee = node.value.func.id
                if callee in allowed_callees:
                    continue
                if not (
                    callee[:1].isupper()
                    or (callee.startswith("_") and len(callee) > 1 and callee[1].isupper())
                ):
                    continue
    
                target_names = [
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                ]
                if not target_names:
                    continue
    
                offenders.append(
                    f"{rel}:{node.lineno} -> {', '.join(target_names)} = {callee}(...)"
                )
    
        assert not offenders, (
            "Backend must avoid module-level class singletons; "
            "instantiate via providers/constructors:\n" + "\n".join(offenders)
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

    def test_routers_do_not_import_threading_module_directly():
        offenders: list[str] = []
        for path in _iter_python_files(ROUTERS_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
    
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "threading":
                            offenders.append(f"{rel}: import threading")
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue
                    module = node.module or ""
                    if module == "threading":
                        offenders.append(f"{rel}: from threading import ...")
    
        assert not offenders, (
            "Routers must delegate background execution to BackgroundTasks/application services, "
            "not import threading directly:\n" + "\n".join(offenders)
        )

    def test_routers_do_not_spawn_manual_threads():
        offenders: list[str] = []
        for path in _iter_python_files(ROUTERS_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
    
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
    
                if isinstance(node.func, ast.Name) and node.func.id == "Thread":
                    offenders.append(f"{rel}:{node.lineno} -> Thread(...)")
                    continue
    
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "threading"
                    and node.func.attr == "Thread"
                ):
                    offenders.append(f"{rel}:{node.lineno} -> threading.Thread(...)")
    
        assert not offenders, (
            "Routers must not spawn manual threads directly:\n" + "\n".join(offenders)
        )

    def test_router_endpoints_do_not_receive_db_parameter():
        offenders: list[str] = []
    
        for path in _iter_python_files(ROUTERS_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
    
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
    
                is_router_endpoint = any(
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "router"
                    and decorator.func.attr in {"get", "post", "put", "delete", "patch"}
                    for decorator in node.decorator_list
                )
                if not is_router_endpoint:
                    continue
    
                all_args = [*node.args.args, *node.args.kwonlyargs]
                if any(arg.arg == "db" for arg in all_args):
                    offenders.append(f"{rel}:{node.lineno}")
    
        assert not offenders, (
            "Route endpoints must not receive DB sessions directly; use request-scoped "
            "context/services built via container:\n" + "\n".join(offenders)
        )

    def test_routers_do_not_use_sessiondep_alias():
        offenders: list[str] = []
    
        for path in _iter_python_files(ROUTERS_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level:
                    continue
                if node.module != "Backend.application.services.service_container":
                    continue
                if any(alias.name == "SessionDep" for alias in node.names):
                    offenders.append(f"{rel}:{node.lineno}")
    
        assert not offenders, (
            "Routers must not use SessionDep directly; "
            "use request-scoped dependency builders from service_container:\n"
            + "\n".join(offenders)
        )

    def test_routers_do_not_access_request_context_db_directly():
        offenders: list[str] = []
    
        for path in _iter_python_files(ROUTERS_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            source = path.read_text(encoding="utf-8-sig")
            if "request_context.db" in source:
                offenders.append(str(rel))
    
        assert not offenders, (
            "Routers must not pass raw db from request_context; "
            "use request-scoped workflow/service methods instead:\n"
            + "\n".join(offenders)
        )

    def test_routers_do_not_define_module_level_runtime_singletons():
        offenders: list[str] = []
        allowed_callees = {
            "APIRouter",
            "OAuth2PasswordBearer",
            "OAuth",
            "FileHandler",
            "Formatter",
        }
    
        for path in _iter_python_files(ROUTERS_ROOT):
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
                if callee in allowed_callees:
                    continue
                if not (
                    callee[:1].isupper()
                    or (callee.startswith("_") and len(callee) > 1 and callee[1].isupper())
                ):
                    continue
    
                target_names = [
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                ]
                if not target_names:
                    continue
    
                offenders.append(
                    f"{rel}:{node.lineno} -> {', '.join(target_names)} = {callee}(...)"
                )
    
        assert not offenders, (
            "Routers must avoid module-level runtime/workflow singletons; "
            "build workflow instances via provider functions:\n" + "\n".join(offenders)
        )

    def test_backend_has_no_legacy_crud_imports():
        offenders: list[str] = []
    
        for path in _iter_python_files(BACKEND_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
    
            if rel.parts[:2] in {("Backend", "tests"), ("Backend", "testing")}:
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
            "Backend must not import legacy crud modules:\n"
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

    def test_repository_access_adapters_module_removed():
        adapters_path = APPLICATION_SERVICES_ROOT / "repository_access_adapters.py"
        assert not adapters_path.exists(), (
            "Legacy repository_access_adapters transitional module should be removed."
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

    def test_application_services_do_not_issue_sqlalchemy_query_directly():
        offenders: list[str] = []
    
        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr != "query":
                    continue
                offenders.append(f"{rel}:{node.lineno}")
    
        assert not offenders, (
            "Backend.application.services must not call Session.query directly; "
            "use repositories from infrastructure layer:\n"
            + "\n".join(offenders)
        )

    def test_application_services_have_no_transition_facade_modules():
        offenders = sorted(
            str(path.relative_to(PROJECT_ROOT))
            for path in APPLICATION_SERVICES_ROOT.rglob("*_facade.py")
            if path.is_file()
        )
        assert not offenders, (
            "Transition facade modules must be removed from application/services:\n"
            + "\n".join(offenders)
        )

    def test_repository_runtime_support_bridge_is_removed():
        runtime_support_path = APPLICATION_SERVICES_ROOT / "repository_runtime_support.py"
        assert not runtime_support_path.exists(), (
            "repository_runtime_support.py must be removed."
        )

        offenders: list[str] = []
        for path in _iter_python_files(BACKEND_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            if rel.parts[:2] in {("Backend", "tests"), ("Backend", "testing")}:
                continue
            source = path.read_text(encoding="utf-8-sig")
            if "call_repository_method(" in source:
                offenders.append(str(rel))

        assert not offenders, (
            "Dynamic repository bridge call_repository_method(...) must not exist:\n"
            + "\n".join(offenders)
        )

    def test_application_service_public_methods_do_not_receive_db_session_factory():
        offenders: list[str] = []

        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name == "__init__":
                    continue
                all_args = [*node.args.args, *node.args.kwonlyargs]
                if any(arg.arg == "db_session_factory" for arg in all_args):
                    offenders.append(f"{rel}:{node.lineno} -> {node.name}")

        assert not offenders, (
            "Public service methods must not accept db_session_factory per call:\n"
            + "\n".join(offenders)
        )

    def test_runtime_modules_do_not_use_global_statement():
        offenders: list[str] = []
        for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Global):
                    offenders.append(f"{rel}:{node.lineno}")

        assert not offenders, (
            "Runtime modules must not use Python 'global' statement:\n"
            + "\n".join(offenders)
        )

    def test_file_and_web_runtime_surfaces_do_not_use_varargs():
        offenders: list[str] = []
        target_files = [
            APPLICATION_SERVICES_ROOT / "file_processing" / "contracts.py",
            APPLICATION_SERVICES_ROOT / "file_processing" / "orchestrator_service.py",
            APPLICATION_SERVICES_ROOT / "web_data_extractor" / "contracts.py",
            APPLICATION_SERVICES_ROOT / "web_data_extractor" / "orchestrator_service.py",
            PROJECT_ROOT / "Backend" / "infrastructure" / "adapters" / "file_processing_adapter.py",
            PROJECT_ROOT / "Backend" / "infrastructure" / "adapters" / "web_data_extractor_adapter.py",
            PROJECT_ROOT / "Backend" / "infrastructure" / "runtime_modules" / "file_processing_module.py",
            PROJECT_ROOT / "Backend" / "infrastructure" / "runtime_modules" / "web_data_extractor_module.py",
        ]

        for path in target_files:
            if not path.exists():
                continue
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.args.vararg is not None:
                    offenders.append(f"{rel}:{node.lineno} -> *{node.args.vararg.arg}")
                if node.args.kwarg is not None:
                    offenders.append(f"{rel}:{node.lineno} -> **{node.args.kwarg.arg}")

        assert not offenders, (
            "Targeted file/web service surfaces must not use *args/**kwargs:\n"
            + "\n".join(offenders)
        )

    def test_router_gateways_do_not_use_kwargs_bridge_methods():
        offenders: list[str] = []
        targets = [
            (ROUTERS_ROOT / "fornecedores.py", "_FornecedoresServiceGateway"),
            (ROUTERS_ROOT / "produtos.py", "ProdutosCatalogCoordinator"),
            (ROUTERS_ROOT / "generation.py", "GenerationRequestService"),
        ]

        for path, class_name in targets:
            if not path.exists():
                continue
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            class_node = next(
                (
                    node
                    for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == class_name
                ),
                None,
            )
            if class_node is None:
                offenders.append(f"{rel}: missing class {class_name}")
                continue

            for node in class_node.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name == "__init__":
                    continue
                if node.args.kwarg is not None:
                    offenders.append(
                        f"{rel}:{node.lineno} -> {class_name}.{node.name}(**{node.args.kwarg.arg})"
                    )

        assert not offenders, (
            "Router gateway/coordinator methods must expose explicit signatures "
            "(no **kwargs bridges):\n" + "\n".join(offenders)
        )

    def test_produtos_coordinator_does_not_use_reflective_dispatch():
        path = ROUTERS_ROOT / "produtos.py"
        rel = path.relative_to(PROJECT_ROOT)
        tree = _parse_python_file(path)
        class_node = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == "ProdutosCatalogCoordinator"
            ),
            None,
        )
        assert class_node is not None, f"{rel}: missing class ProdutosCatalogCoordinator"

        offenders: list[str] = []
        forbidden_method_names = {"_runtime_method", "_invoke_async", "set_default_runtime"}
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden_method_names:
                offenders.append(f"{rel}:{node.lineno} -> method {node.name}")

        for node in ast.walk(class_node):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "getattr":
                continue
            if len(node.args) < 2:
                continue
            if isinstance(node.args[1], ast.Name) and node.args[1].id == "method_name":
                offenders.append(f"{rel}:{node.lineno} -> getattr(..., method_name)")

        assert not offenders, (
            "ProdutosCatalogCoordinator must not use reflective string dispatch:\n"
            + "\n".join(offenders)
        )

    def test_generation_flow_surfaces_do_not_use_var_kwargs():
        offenders: list[str] = []
        targets = [
            (ROUTERS_ROOT / "generation.py", "GenerationRequestService"),
            (APPLICATION_SERVICES_ROOT / "generation_task_service.py", "GenerationTaskService"),
        ]

        for path, class_name in targets:
            if not path.exists():
                continue
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            class_node = next(
                (
                    node
                    for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == class_name
                ),
                None,
            )
            if class_node is None:
                offenders.append(f"{rel}: missing class {class_name}")
                continue
            for node in class_node.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name == "__init__":
                    continue
                if node.args.kwarg is not None:
                    offenders.append(
                        f"{rel}:{node.lineno} -> {class_name}.{node.name}(**{node.args.kwarg.arg})"
                    )

        assert not offenders, (
            "Generation router/service surfaces must use explicit typed parameters (no **kwargs):\n"
            + "\n".join(offenders)
        )

    def test_application_services_do_not_use_inspect_isclass_resolution():
        offenders: list[str] = []
        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            source = path.read_text(encoding="utf-8-sig")
            if "inspect.isclass(" in source:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))

        assert not offenders, (
            "Application services must not resolve dependencies via inspect.isclass(...):\n"
            + "\n".join(offenders)
        )

    def test_application_services_do_not_use_isinstance_type_resolution():
        offenders: list[str] = []
        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Name) or node.func.id != "isinstance":
                    continue
                if len(node.args) < 2:
                    continue
                type_arg = node.args[1]
                if isinstance(type_arg, ast.Name) and type_arg.id == "type":
                    offenders.append(f"{rel}:{node.lineno}")
                    continue
                if isinstance(type_arg, ast.Tuple):
                    if any(isinstance(elt, ast.Name) and elt.id == "type" for elt in type_arg.elts):
                        offenders.append(f"{rel}:{node.lineno}")

        assert not offenders, (
            "Application services must not resolve dependencies via isinstance(..., type):\n"
            + "\n".join(offenders)
        )

    def test_application_service_public_methods_do_not_take_optional_repo_overrides():
        offenders: list[str] = []

        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)

            for class_node in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                for node in class_node.body:
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if node.name == "__init__" or node.name.startswith("_"):
                        continue

                    positional_args = node.args.args
                    for arg in positional_args:
                        if arg.arg in {"self", "cls"}:
                            continue
                        if not (
                            arg.arg.endswith("_repo")
                            or arg.arg.endswith("_repository")
                            or arg.arg.endswith("_repo_cls")
                            or arg.arg.endswith("_repository_cls")
                        ):
                            continue
                        offenders.append(
                            f"{rel}:{node.lineno} -> {class_node.name}.{node.name}({arg.arg})"
                        )

                    for kw_arg in node.args.kwonlyargs:
                        if kw_arg.arg in {"self", "cls"}:
                            continue
                        if not (
                            kw_arg.arg.endswith("_repo")
                            or kw_arg.arg.endswith("_repository")
                            or kw_arg.arg.endswith("_repo_cls")
                            or kw_arg.arg.endswith("_repository_cls")
                        ):
                            continue
                        offenders.append(
                            f"{rel}:{node.lineno} -> {class_node.name}.{node.name}({kw_arg.arg})"
                        )

        assert not offenders, (
            "Public service methods must not receive repository dependencies as parameters. "
            "Repositories must be constructor-injected only:\n"
            + "\n".join(offenders)
        )

    def test_application_service_constructor_repository_dependencies_are_required():
        offenders: list[str] = []

        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)

            for class_node in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                init_node = next(
                    (
                        node
                        for node in class_node.body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == "__init__"
                    ),
                    None,
                )
                if init_node is None:
                    continue

                positional_args = init_node.args.args
                positional_defaults = [None] * (
                    len(positional_args) - len(init_node.args.defaults)
                ) + list(init_node.args.defaults)
                for arg, default in zip(positional_args, positional_defaults):
                    if arg.arg in {"self", "cls"}:
                        continue
                    if not (
                        arg.arg.endswith("_repo")
                        or arg.arg.endswith("_repository")
                        or arg.arg.endswith("_repo_cls")
                        or arg.arg.endswith("_repository_cls")
                    ):
                        continue
                    if default is not None:
                        offenders.append(
                            f"{rel}:{init_node.lineno} -> {class_node.name}.__init__({arg.arg})"
                        )

                for kw_arg, default in zip(init_node.args.kwonlyargs, init_node.args.kw_defaults):
                    if kw_arg.arg in {"self", "cls"}:
                        continue
                    if not (
                        kw_arg.arg.endswith("_repo")
                        or kw_arg.arg.endswith("_repository")
                        or kw_arg.arg.endswith("_repo_cls")
                        or kw_arg.arg.endswith("_repository_cls")
                    ):
                        continue
                    if default is not None:
                        offenders.append(
                            f"{rel}:{init_node.lineno} -> {class_node.name}.__init__({kw_arg.arg})"
                        )

        assert not offenders, (
            "Application service constructors must require explicit repository dependencies "
            "(no default/optional repo args):\n"
            + "\n".join(offenders)
        )

    def test_application_service_constructors_do_not_use_repo_cls_parameters():
        offenders: list[str] = []

        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)

            for class_node in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                init_node = next(
                    (
                        node
                        for node in class_node.body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == "__init__"
                    ),
                    None,
                )
                if init_node is None:
                    continue

                for arg in [*init_node.args.args, *init_node.args.kwonlyargs]:
                    if arg.arg in {"self", "cls"}:
                        continue
                    if arg.arg.endswith("_repo_cls") or arg.arg.endswith("_repository_cls"):
                        offenders.append(
                            f"{rel}:{init_node.lineno} -> {class_node.name}.__init__({arg.arg})"
                        )

        assert not offenders, (
            "Application service constructors must accept explicit repository providers, "
            "not *_repo_cls/*_repository_cls parameters:\n"
            + "\n".join(offenders)
        )

    def test_application_services_do_not_use_local_repository_imports():
        offenders: list[str] = []

        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            parent_by_node: dict[ast.AST, ast.AST] = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parent_by_node[child] = parent

            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level:
                    continue
                module = node.module or ""
                if not module.startswith("Backend.infrastructure.repositories"):
                    continue

                current = parent_by_node.get(node)
                in_function_scope = False
                while current is not None:
                    if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        in_function_scope = True
                        break
                    current = parent_by_node.get(current)

                if in_function_scope:
                    offenders.append(f"{rel}:{node.lineno} -> from {module} import ...")

        assert not offenders, (
            "Application services must not perform local/fallback imports for repositories; "
            "dependencies must be constructor-injected:\n"
            + "\n".join(offenders)
        )

    def test_routers_do_not_mutate_private_attributes_of_external_objects():
        offenders: list[str] = []

        for path in _iter_python_files(ROUTERS_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            tree = _parse_python_file(path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if not isinstance(target, ast.Attribute):
                        continue
                    if not target.attr.startswith("_") or target.attr.startswith("__"):
                        continue
                    owner = target.value
                    if isinstance(owner, ast.Name) and owner.id == "self":
                        continue
                    offenders.append(f"{rel}:{node.lineno}")

        assert not offenders, (
            "Routers must not mutate private fields of external objects "
            "(compose dependencies via constructors):\n"
            + "\n".join(offenders)
        )

    def test_application_services_do_not_use_typeerror_fallback_dependency_resolution():
        offenders: list[str] = []

        for path in _iter_python_files(APPLICATION_SERVICES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            source = path.read_text(encoding="utf-8-sig")
            if "except TypeError" in source:
                offenders.append(str(rel))

        assert not offenders, (
            "Application services must not rely on TypeError-based fallback dependency "
            "resolution (explicit providers only):\n"
            + "\n".join(offenders)
        )

    def test_runtime_modules_do_not_use_legacy_crud_alias_parameters():
        offenders: list[str] = []

        for path in _iter_python_files(INFRASTRUCTURE_RUNTIME_MODULES_ROOT):
            rel = path.relative_to(PROJECT_ROOT)
            source = path.read_text(encoding="utf-8-sig")
            if "crud_module" in source or "crud_users_module" in source:
                offenders.append(str(rel))

        assert not offenders, (
            "Runtime modules must not use legacy crud alias parameters "
            "(crud_module/crud_users_module):\n"
            + "\n".join(offenders)
        )

    def test_limit_runtime_module_has_no_typeerror_signature_fallbacks():
        limit_module_path = INFRASTRUCTURE_RUNTIME_MODULES_ROOT / "limit_module.py"
        source = limit_module_path.read_text(encoding="utf-8-sig")
        assert "except TypeError" not in source, (
            "Limit runtime module must not use TypeError fallback for dependency "
            "signature compatibility."
        )

    def test_ia_and_limit_services_require_explicit_port_dependency():
        offenders: list[str] = []
        targets = [
            APPLICATION_SERVICES_ROOT / "ia_generation_service.py",
            APPLICATION_SERVICES_ROOT / "limit_service.py",
        ]

        for path in targets:
            rel = path.relative_to(PROJECT_ROOT)
            source = path.read_text(encoding="utf-8-sig")
            if "| None = None" in source and "port:" in source:
                offenders.append(f"{rel}: optional port dependency")
            if "or IAGenerationServiceAdapter(" in source:
                offenders.append(f"{rel}: fallback adapter instantiation")
            if "or LimitServiceAdapter(" in source:
                offenders.append(f"{rel}: fallback adapter instantiation")

        assert not offenders, (
            "IA/Limit services must receive explicit injected ports "
            "(no optional/default adapter fallback):\n"
            + "\n".join(offenders)
        )

    def test_tasks_module_has_no_procedural_sqlalchemy_runtime_construction():
        tasks_path = BACKEND_ROOT / "tasks.py"
        source = tasks_path.read_text(encoding="utf-8-sig")
        offenders: list[str] = []
        for pattern in ("create_engine(", "sessionmaker(", "db.query("):
            if pattern in source:
                offenders.append(pattern)

        assert not offenders, (
            "Backend/tasks.py must delegate persistence via OO services/repositories "
            "(no procedural SQLAlchemy runtime setup):\n"
            + "\n".join(offenders)
        )

    def test_file_processing_runtime_has_no_direct_catalog_import_file_query():
        runtime_path = INFRASTRUCTURE_RUNTIME_MODULES_ROOT / "file_processing_module.py"
        source = runtime_path.read_text(encoding="utf-8-sig")
        assert "db.query(models.CatalogImportFile)" not in source, (
            "File processing runtime module must not query CatalogImportFile directly; "
            "use injected repository/service."
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

    def test_produtos_core_endpoints_do_not_receive_db_session_directly():
        produtos_router_path = ROUTERS_ROOT / "produtos.py"
        tree = _parse_python_file(produtos_router_path)
        offenders: list[str] = []
        endpoint_names = {
            "create_produto",
            "read_produto",
            "read_produtos",
            "update_produto",
            "delete_produto",
            "batch_delete_produtos",
            "upload_produto_image",
        }
    
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name not in endpoint_names:
                continue
    
            is_router_endpoint = any(
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "router"
                and decorator.func.attr in {"get", "post", "put", "delete", "patch"}
                for decorator in node.decorator_list
            )
            if not is_router_endpoint:
                continue
    
            all_args = [*node.args.args, *node.args.kwonlyargs]
            if any(arg.arg == "db" for arg in all_args):
                offenders.append(f"{produtos_router_path.relative_to(PROJECT_ROOT)}:{node.lineno}")
    
        assert not offenders, (
            "Core produtos endpoints must use request-scoped service dependencies, "
            "not receive db sessions directly:\n" + "\n".join(offenders)
        )

_iter_python_files = _TopLevelFunctionSurface._iter_python_files
_parse_python_file = _TopLevelFunctionSurface._parse_python_file
_import_targets = _TopLevelFunctionSurface._import_targets
_is_http_endpoint_function = _TopLevelFunctionSurface._is_http_endpoint_function
test_application_does_not_import_backend_services_modules = _TopLevelFunctionSurface.test_application_does_not_import_backend_services_modules
test_application_does_not_import_backend_router_modules = _TopLevelFunctionSurface.test_application_does_not_import_backend_router_modules
test_application_services_do_not_define_dunder_getattr_fallbacks = _TopLevelFunctionSurface.test_application_services_do_not_define_dunder_getattr_fallbacks
test_application_services_do_not_import_legacy_infrastructure_bridges = _TopLevelFunctionSurface.test_application_services_do_not_import_legacy_infrastructure_bridges
test_application_services_do_not_call_private_methods_from_external_objects = _TopLevelFunctionSurface.test_application_services_do_not_call_private_methods_from_external_objects
test_infrastructure_adapters_do_not_import_backend_services_modules = _TopLevelFunctionSurface.test_infrastructure_adapters_do_not_import_backend_services_modules
test_infrastructure_runtime_providers_do_not_import_backend_services_modules = _TopLevelFunctionSurface.test_infrastructure_runtime_providers_do_not_import_backend_services_modules
test_infrastructure_runtime_providers_do_not_import_runtime_modules_directly = _TopLevelFunctionSurface.test_infrastructure_runtime_providers_do_not_import_runtime_modules_directly
test_runtime_modules_imports_are_constrained_to_runtime_services_and_tests = _TopLevelFunctionSurface.test_runtime_modules_imports_are_constrained_to_runtime_services_and_tests
test_backend_tests_do_not_import_runtime_modules_directly = _TopLevelFunctionSurface.test_backend_tests_do_not_import_runtime_modules_directly
test_project_tests_do_not_import_runtime_modules_directly = _TopLevelFunctionSurface.test_project_tests_do_not_import_runtime_modules_directly
test_infrastructure_runtime_providers_expose_get_runtime_service_only = _TopLevelFunctionSurface.test_infrastructure_runtime_providers_expose_get_runtime_service_only
test_backend_top_level_non_endpoint_functions_are_allowlisted = _TopLevelFunctionSurface.test_backend_top_level_non_endpoint_functions_are_allowlisted
test_runtime_services_do_not_import_backend_services_modules = _TopLevelFunctionSurface.test_runtime_services_do_not_import_backend_services_modules
test_runtime_services_do_not_call_runtime_module_functions_directly = _TopLevelFunctionSurface.test_runtime_services_do_not_call_runtime_module_functions_directly
test_backend_code_does_not_import_backend_services_modules = _TopLevelFunctionSurface.test_backend_code_does_not_import_backend_services_modules
test_runtime_modules_do_not_import_backend_crud_package_root = _TopLevelFunctionSurface.test_runtime_modules_do_not_import_backend_crud_package_root
test_runtime_modules_do_not_expose_public_function_wrappers = _TopLevelFunctionSurface.test_runtime_modules_do_not_expose_public_function_wrappers
test_runtime_modules_do_not_define_top_level_functions = _TopLevelFunctionSurface.test_runtime_modules_do_not_define_top_level_functions
test_crud_modules_do_not_expose_public_function_wrappers = _TopLevelFunctionSurface.test_crud_modules_do_not_expose_public_function_wrappers
test_runtime_modules_do_not_instantiate_singletons_at_module_scope = _TopLevelFunctionSurface.test_runtime_modules_do_not_instantiate_singletons_at_module_scope
test_runtime_services_do_not_instantiate_singletons_at_module_scope = _TopLevelFunctionSurface.test_runtime_services_do_not_instantiate_singletons_at_module_scope
test_backend_code_does_not_define_module_level_class_singletons = _TopLevelFunctionSurface.test_backend_code_does_not_define_module_level_class_singletons
test_crud_modules_do_not_instantiate_singletons_at_module_scope = _TopLevelFunctionSurface.test_crud_modules_do_not_instantiate_singletons_at_module_scope
test_routers_do_not_import_backend_crud_modules_directly = _TopLevelFunctionSurface.test_routers_do_not_import_backend_crud_modules_directly
test_routers_do_not_import_application_services_package_root = _TopLevelFunctionSurface.test_routers_do_not_import_application_services_package_root
test_routers_do_not_import_threading_module_directly = _TopLevelFunctionSurface.test_routers_do_not_import_threading_module_directly
test_routers_do_not_spawn_manual_threads = _TopLevelFunctionSurface.test_routers_do_not_spawn_manual_threads
test_router_endpoints_do_not_receive_db_parameter = _TopLevelFunctionSurface.test_router_endpoints_do_not_receive_db_parameter
test_routers_do_not_use_sessiondep_alias = _TopLevelFunctionSurface.test_routers_do_not_use_sessiondep_alias
test_routers_do_not_access_request_context_db_directly = _TopLevelFunctionSurface.test_routers_do_not_access_request_context_db_directly
test_routers_do_not_define_module_level_runtime_singletons = _TopLevelFunctionSurface.test_routers_do_not_define_module_level_runtime_singletons
test_backend_has_no_legacy_crud_imports = _TopLevelFunctionSurface.test_backend_has_no_legacy_crud_imports
test_tests_do_not_import_backend_crud_modules_directly = _TopLevelFunctionSurface.test_tests_do_not_import_backend_crud_modules_directly
test_repository_access_adapters_module_removed = _TopLevelFunctionSurface.test_repository_access_adapters_module_removed
test_application_services_package_init_has_no_eager_reexports = _TopLevelFunctionSurface.test_application_services_package_init_has_no_eager_reexports
test_application_services_do_not_issue_sqlalchemy_query_directly = _TopLevelFunctionSurface.test_application_services_do_not_issue_sqlalchemy_query_directly
test_application_services_have_no_transition_facade_modules = _TopLevelFunctionSurface.test_application_services_have_no_transition_facade_modules
test_repository_runtime_support_bridge_is_removed = _TopLevelFunctionSurface.test_repository_runtime_support_bridge_is_removed
test_application_service_public_methods_do_not_receive_db_session_factory = _TopLevelFunctionSurface.test_application_service_public_methods_do_not_receive_db_session_factory
test_runtime_modules_do_not_use_global_statement = _TopLevelFunctionSurface.test_runtime_modules_do_not_use_global_statement
test_file_and_web_runtime_surfaces_do_not_use_varargs = _TopLevelFunctionSurface.test_file_and_web_runtime_surfaces_do_not_use_varargs
test_router_gateways_do_not_use_kwargs_bridge_methods = _TopLevelFunctionSurface.test_router_gateways_do_not_use_kwargs_bridge_methods
test_produtos_coordinator_does_not_use_reflective_dispatch = _TopLevelFunctionSurface.test_produtos_coordinator_does_not_use_reflective_dispatch
test_generation_flow_surfaces_do_not_use_var_kwargs = _TopLevelFunctionSurface.test_generation_flow_surfaces_do_not_use_var_kwargs
test_application_services_do_not_use_inspect_isclass_resolution = _TopLevelFunctionSurface.test_application_services_do_not_use_inspect_isclass_resolution
test_application_services_do_not_use_isinstance_type_resolution = _TopLevelFunctionSurface.test_application_services_do_not_use_isinstance_type_resolution
test_application_service_public_methods_do_not_take_optional_repo_overrides = _TopLevelFunctionSurface.test_application_service_public_methods_do_not_take_optional_repo_overrides
test_application_service_constructor_repository_dependencies_are_required = _TopLevelFunctionSurface.test_application_service_constructor_repository_dependencies_are_required
test_application_service_constructors_do_not_use_repo_cls_parameters = _TopLevelFunctionSurface.test_application_service_constructors_do_not_use_repo_cls_parameters
test_application_services_do_not_use_local_repository_imports = _TopLevelFunctionSurface.test_application_services_do_not_use_local_repository_imports
test_routers_do_not_mutate_private_attributes_of_external_objects = _TopLevelFunctionSurface.test_routers_do_not_mutate_private_attributes_of_external_objects
test_application_services_do_not_use_typeerror_fallback_dependency_resolution = _TopLevelFunctionSurface.test_application_services_do_not_use_typeerror_fallback_dependency_resolution
test_runtime_modules_do_not_use_legacy_crud_alias_parameters = _TopLevelFunctionSurface.test_runtime_modules_do_not_use_legacy_crud_alias_parameters
test_limit_runtime_module_has_no_typeerror_signature_fallbacks = _TopLevelFunctionSurface.test_limit_runtime_module_has_no_typeerror_signature_fallbacks
test_ia_and_limit_services_require_explicit_port_dependency = _TopLevelFunctionSurface.test_ia_and_limit_services_require_explicit_port_dependency
test_tasks_module_has_no_procedural_sqlalchemy_runtime_construction = _TopLevelFunctionSurface.test_tasks_module_has_no_procedural_sqlalchemy_runtime_construction
test_file_processing_runtime_has_no_direct_catalog_import_file_query = _TopLevelFunctionSurface.test_file_processing_runtime_has_no_direct_catalog_import_file_query
test_tests_do_not_import_private_backend_symbols = _TopLevelFunctionSurface.test_tests_do_not_import_private_backend_symbols
test_produtos_core_endpoints_do_not_receive_db_session_directly = _TopLevelFunctionSurface.test_produtos_core_endpoints_do_not_receive_db_session_directly




















































































