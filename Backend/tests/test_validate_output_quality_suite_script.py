"""Tests for the aggregate output quality validation suite script."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_output_quality_suite.py"
SPEC = importlib.util.spec_from_file_location("validate_output_quality_suite", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_suite_builds_expected_case_list():
    args = MODULE.parse_args.__globals__["argparse"].Namespace(
        base_url="http://127.0.0.1:8017",
        lm_model="google/gemma-3-12b",
        eval_max_cases=0,
        workflow_max_cases=0,
        report_path="report.json",
    )

    cases = MODULE._case_command(args)

    assert [case["name"] for case in cases] == [
        "evals_local_lm",
        "workflow_local_lm",
        "catalog_demdaco_product",
        "catalog_sharperbags_rejected",
    ]
    assert "--expect-no-products" in cases[-1]["command"]


def test_suite_builds_case_list_with_local_smoke_limits():
    args = MODULE.parse_args.__globals__["argparse"].Namespace(
        base_url="http://127.0.0.1:8000",
        lm_model="google/gemma-3-12b",
        eval_max_cases=6,
        workflow_max_cases=8,
        report_path="report.json",
    )

    cases = MODULE._case_command(args)

    assert "--max-cases" in cases[0]["command"]
    assert "6" in cases[0]["command"]
    assert "--max-cases" in cases[1]["command"]
    assert "8" in cases[1]["command"]


def test_run_case_reports_stdout_and_success(monkeypatch):
    class Completed:
        def __init__(self, returncode, stdout, stderr):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    monkeypatch.setattr(
        MODULE.subprocess,
        "run",
        lambda *args, **kwargs: Completed(0, "ok", ""),
    )

    result = MODULE.run_case({"name": "case", "command": ["python", "x.py"]})

    assert result["ok"] is True
    assert result["stdout"] == "ok"
    assert result["stderr"] == ""
