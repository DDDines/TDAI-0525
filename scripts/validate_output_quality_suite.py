"""Run a repeatable local validation suite for LLM quality and real catalog flows."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the local quality validation suite."""
    parser = argparse.ArgumentParser(description="Run the local CatalogAI output quality suite.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8017", help="Backend base URL without /api/v1.")
    parser.add_argument("--lm-model", default="google/gemma-3-12b", help="LM Studio model identifier.")
    parser.add_argument(
        "--eval-max-cases",
        type=int,
        default=0,
        help="Optional limit passed to run_evals.py for faster local smoke runs.",
    )
    parser.add_argument(
        "--workflow-max-cases",
        type=int,
        default=0,
        help="Optional limit passed to validate_local_llm_workflow.py for faster local smoke runs.",
    )
    parser.add_argument(
        "--report-path",
        default=str(RUNTIME_DIR / "output-quality-suite-report.json"),
        help="Path to write the aggregate JSON report.",
    )
    return parser.parse_args()


def _case_command(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """Return the built-in suite cases."""
    eval_command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_evals.py"),
        "--base-url",
        "http://127.0.0.1:1234/v1",
        "--model",
        args.lm_model,
    ]
    if args.eval_max_cases and args.eval_max_cases > 0:
        eval_command.extend(["--max-cases", str(args.eval_max_cases)])

    workflow_command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "validate_local_llm_workflow.py"),
        "--base-url",
        args.base_url,
        "--lm-model",
        args.lm_model,
    ]
    if args.workflow_max_cases and args.workflow_max_cases > 0:
        workflow_command.extend(["--max-cases", str(args.workflow_max_cases)])

    return [
        {
            "name": "evals_local_lm",
            "command": eval_command,
        },
        {
            "name": "workflow_local_lm",
            "command": workflow_command,
        },
        {
            "name": "catalog_demdaco_product",
            "command": [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "validate_real_catalog_pipeline.py"),
                "--base-url",
                args.base_url,
                "--flow",
                "fornecedores",
                "--catalog-url",
                "https://www.demdaco.com/content/pdfs/2019_PriceIncreaseList.pdf",
                "--catalog-path",
                str(RUNTIME_DIR / "suite-demdaco.pdf"),
                "--report-path",
                str(RUNTIME_DIR / "suite-demdaco-report.json"),
                "--sample-products",
                "3",
            ],
        },
        {
            "name": "catalog_sharperbags_rejected",
            "command": [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "validate_real_catalog_pipeline.py"),
                "--base-url",
                args.base_url,
                "--flow",
                "fornecedores",
                "--catalog-url",
                "https://www.sharperbags.com/PDF/SharperBags_Booklet_2025.pdf",
                "--catalog-path",
                str(RUNTIME_DIR / "suite-sharperbags.pdf"),
                "--report-path",
                str(RUNTIME_DIR / "suite-sharperbags-report.json"),
                "--sample-products",
                "1",
                "--expect-no-products",
            ],
        },
    ]


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Run one validation case and capture stdout/stderr/result."""
    completed = subprocess.run(
        case["command"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "name": case["name"],
        "command": case["command"],
        "returncode": completed.returncode,
        "stdout": str(completed.stdout or "").strip(),
        "stderr": str(completed.stderr or "").strip(),
        "ok": completed.returncode == 0,
    }


def main() -> int:
    """Run the full suite and write an aggregate report."""
    args = parse_args()
    results = [run_case(case) for case in _case_command(args)]
    ok = all(item["ok"] for item in results)
    report = {
        "ok": ok,
        "cases": results,
    }
    rendered_report = json.dumps(report, ensure_ascii=False, indent=2)
    Path(args.report_path).write_text(rendered_report, encoding="utf-8")
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write((rendered_report + "\n").encode(sys.stdout.encoding or "utf-8", errors="replace"))
    else:  # pragma: no cover - legacy stdout fallback
        print(rendered_report.encode("ascii", errors="replace").decode("ascii"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
