"""Module test workflow runtime contract.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import ast
from pathlib import Path


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _iter_backend_modules():
        """Execute _iter_backend_modules.

        This callable is documented to make behavior explicit for readers.
        """
        backend_root = Path(__file__).resolve().parents[1]
        for file_path in backend_root.rglob("*.py"):
            if file_path.name.startswith("test_"):
                continue
            yield file_path

    def test_all_workflow_classes_support_runtime_in_init():
        """Execute test_all_workflow_classes_support_runtime_in_init.

        This callable is documented to make behavior explicit for readers.
        """
        missing_runtime = []
    
        for file_path in _iter_backend_modules():
            source = file_path.read_text(encoding="utf-8-sig")
            tree = ast.parse(source)
    
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if not (node.name.startswith("_") and node.name.endswith("Workflow")):
                    continue
    
                init_method = None
                for class_item in node.body:
                    if isinstance(class_item, ast.FunctionDef) and class_item.name == "__init__":
                        init_method = class_item
                        break
    
                if init_method is None:
                    missing_runtime.append((str(file_path), node.name, "missing __init__"))
                    continue
    
                arg_names = [arg.arg for arg in init_method.args.args]
                kwonly_arg_names = [arg.arg for arg in init_method.args.kwonlyargs]
                all_args = set(arg_names + kwonly_arg_names)
                if "runtime" not in all_args:
                    missing_runtime.append((str(file_path), node.name, "missing runtime arg"))
    
        assert not missing_runtime, f"Workflow sem suporte a runtime: {missing_runtime}"

    def test_internal_workflow_runtime_class_names_are_unique():
        """Execute test_internal_workflow_runtime_class_names_are_unique.

        This callable is documented to make behavior explicit for readers.
        """
        class_locations: dict[str, list[str]] = {}
        valid_suffixes = ("Workflow", "Runtime", "EngineRuntime")
    
        for file_path in _iter_backend_modules():
            source = file_path.read_text(encoding="utf-8-sig")
            tree = ast.parse(source)
    
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not node.name.startswith("_"):
                    continue
                if not node.name.endswith(valid_suffixes):
                    continue
                class_locations.setdefault(node.name, []).append(f"{file_path}:{node.lineno}")
    
        duplicated = {name: locs for name, locs in class_locations.items() if len(locs) > 1}
        assert not duplicated, f"Classes internas OOP duplicadas encontradas: {duplicated}"

_iter_backend_modules = _TopLevelFunctionSurface._iter_backend_modules
test_all_workflow_classes_support_runtime_in_init = _TopLevelFunctionSurface.test_all_workflow_classes_support_runtime_in_init
test_internal_workflow_runtime_class_names_are_unique = _TopLevelFunctionSurface.test_internal_workflow_runtime_class_names_are_unique




