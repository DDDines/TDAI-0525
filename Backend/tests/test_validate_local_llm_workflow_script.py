"""Tests for the local LM Studio workflow validation script helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_local_llm_workflow.py"
SPEC = importlib.util.spec_from_file_location("validate_local_llm_workflow", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_validate_generated_text_flags_boilerplate_and_missing_identity():
    issues = MODULE.validate_generated_text(
        output_text="Compra online com entrega rapida. Ligue agora para 11 99999-0000.",
        required_tokens=("bosch", "bomba", "12v"),
        min_words=3,
        max_words=40,
    )

    assert "telefone ou bloco numerico suspeito" in issues
    assert any(issue.startswith("boilerplate comercial:") for issue in issues)
    assert "identidade do produto insuficiente" in issues


def test_validate_generated_text_accepts_concrete_product_copy():
    issues = MODULE.validate_generated_text(
        output_text=(
            "Bomba de combustivel Bosch 12V com pressao estavel, baixo ruido "
            "e aplicacao em motores flex."
        ),
        required_tokens=("bosch", "bomba", "12v"),
        min_words=8,
        max_words=40,
    )

    assert issues == []


def test_build_smoke_product_payload_contains_realistic_identity():
    payload = MODULE.build_smoke_product_payload(fornecedor_id=7, product_type_id=9)

    assert payload["fornecedor_id"] == 7
    assert payload["product_type_id"] == 9
    assert "bosch" in payload["nome_base"].lower()
    assert payload["dynamic_attributes"]["voltagem"] == "12V"
    assert payload["sku"].startswith("LLM-SMOKE-")


def test_contains_suspicious_contact_number_ignores_reference_code_context():
    assert (
        MODULE.contains_suspicious_contact_number(
            "Modelo F000TE1773 referencia 0580454094 com pressao estavel."
        )
        is False
    )
    assert MODULE.contains_suspicious_contact_number("Ligue agora para 11 99999-0000.") is True
