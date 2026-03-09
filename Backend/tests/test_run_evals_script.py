"""Tests for local eval guardrails around title identity preservation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_evals.py"
SPEC = importlib.util.spec_from_file_location("run_evals_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_normalize_eval_output_preserves_source_identity_for_titles():
    case = {
        "type": "title",
        "input": {"nome_base": "Always a Princess Crown Frame"},
    }

    output = MODULE.normalize_eval_output(
        case,
        "1. Tiara Corona Sempre Uma Princesa\n2. Moldura Princess Crown",
    )

    assert output == "Always a Princess Crown Frame"


def test_validate_case_flags_loss_of_original_title_identity():
    case = {
        "type": "title",
        "input": {"nome_base": "Always a Princess Crown Frame"},
        "must_include_any": ["princess"],
        "must_preserve_tokens": ["always", "princess", "crown", "frame"],
        "must_preserve_tokens_min_count": 3,
    }

    passed, issues = MODULE.validate_case(case, "Moldura Princess Crown")

    assert passed is False
    assert any(issue.startswith("perda de identidade do nome original:") for issue in issues)


def test_validate_case_allows_short_title_when_source_identity_is_preserved():
    case = {
        "type": "title",
        "input": {"nome_base": "Paralama Dianteiro"},
        "min_words": 3,
        "must_include_any": ["paralama"],
    }

    passed, issues = MODULE.validate_case(case, "Paralama Dianteiro")

    assert passed is True
    assert issues == []


def test_load_dataset_accepts_utf8_bom(tmp_path):
    dataset_path = tmp_path / "catalog_gold_cases.json"
    payload = [
        {
            "id": "case-bom",
            "type": "title",
            "input": {"nome_base": "Produto"},
        }
    ]
    dataset_path.write_text(json.dumps(payload), encoding="utf-8-sig")

    loaded = MODULE.load_dataset(dataset_path)

    assert loaded[0]["id"] == "case-bom"
