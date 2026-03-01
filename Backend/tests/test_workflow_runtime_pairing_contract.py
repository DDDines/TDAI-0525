from __future__ import annotations

import ast
from pathlib import Path


class _TopLevelFunctionSurface:

    def _collect_class_names(backend_root: Path):
        workflow_names: set[str] = set()
        runtime_names: set[str] = set()
    
        for py_file in backend_root.rglob("*.py"):
            if "tests" in py_file.parts:
                continue
    
            source = py_file.read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(py_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                class_name = node.name
                if class_name.startswith("_") and class_name.endswith("Workflow"):
                    workflow_names.add(class_name)
                if class_name.startswith("_") and class_name.endswith("Runtime"):
                    runtime_names.add(class_name)
    
        return workflow_names, runtime_names

    def test_every_workflow_has_matching_runtime_class():
        backend_root = Path(__file__).resolve().parents[1]
        workflow_names, runtime_names = _collect_class_names(backend_root)
    
        missing_pairs = []
        for workflow_name in sorted(workflow_names):
            expected_runtime_name = workflow_name.replace("Workflow", "Runtime")
            if expected_runtime_name not in runtime_names:
                missing_pairs.append((workflow_name, expected_runtime_name))
    
        assert not missing_pairs, (
            "Workflows sem Runtime correspondente encontrados: "
            + ", ".join(f"{w}->{r}" for w, r in missing_pairs)
        )

_collect_class_names = _TopLevelFunctionSurface._collect_class_names
test_every_workflow_has_matching_runtime_class = _TopLevelFunctionSurface.test_every_workflow_has_matching_runtime_class


