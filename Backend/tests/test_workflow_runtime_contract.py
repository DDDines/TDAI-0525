import ast
from pathlib import Path


def test_all_workflow_classes_support_runtime_in_init():
    backend_root = Path(__file__).resolve().parents[1]
    missing_runtime = []

    for file_path in backend_root.rglob("*.py"):
        if file_path.name.startswith("test_"):
            continue

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
