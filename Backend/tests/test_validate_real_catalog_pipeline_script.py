"""Tests for the real catalog pipeline validation script helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_real_catalog_pipeline.py"
SPEC = importlib.util.spec_from_file_location("validate_real_catalog_pipeline", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_pick_product_type_id_prefers_type_without_templates():
    product_types = [
        {"id": 1, "attribute_templates": [{"attribute_key": "marca"}]},
        {"id": 3, "attribute_templates": []},
        {"id": 2, "attribute_templates": [{"attribute_key": "cor"}]},
    ]

    assert MODULE.pick_product_type_id(product_types, None) == 3
    assert MODULE.pick_product_type_id(product_types, 9) == 9


def test_extract_created_items_normalizes_result_summary():
    result_summary = {
        "created": [{"id": 10, "nome_base": "Produto 1"}, {"id": 11, "nome_base": "Produto 2"}],
        "updated": [],
    }

    assert MODULE.extract_created_items(result_summary) == result_summary["created"]
    assert MODULE.extract_created_items({"created": "invalido"}) == []
    assert MODULE.extract_created_items(None) == []


def test_validate_generated_product_snapshot_accepts_clean_output():
    snapshot = {
        "status_titulo_ia": "CONCLUIDO",
        "status_descricao_ia": "CONCLUIDO",
        "titulos": [
            "Always a Princess Crown Frame",
            "Moldura Princess Crown",
            "Porta Retrato Princess Crown",
        ],
        "descricao": (
            "Transforme momentos especiais em lembranças duradouras com o Always a Princess "
            "Crown Frame, um porta-retrato delicado e elegante para destacar fotos infantis."
        ),
    }

    assert MODULE.validate_generated_product_snapshot(snapshot) == []


def test_validate_generated_product_snapshot_flags_missing_titles_and_contact_noise():
    snapshot = {
        "status_titulo_ia": "FALHA",
        "status_descricao_ia": "CONCLUIDO",
        "titulos": ["Titulo unico"],
        "descricao": "Compra online com entrega rapida. Ligue agora para 11 99999-0000 e visite www.exemplo.com.",
    }

    issues = MODULE.validate_generated_product_snapshot(snapshot)

    assert "status de titulo nao concluiu" in issues
    assert "menos de 3 titulos sugeridos" in issues
    assert "descricao com telefone suspeito" in issues
    assert "descricao com url" in issues
    assert any(issue.startswith("descricao com boilerplate comercial:") for issue in issues)
