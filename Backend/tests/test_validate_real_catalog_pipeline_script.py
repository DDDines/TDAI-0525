"""Tests for the real catalog pipeline validation script helpers."""

from __future__ import annotations

import argparse
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


def test_summarize_flow_payload_reduces_large_created_lists():
    payload = {
        "status": "IMPORTED",
        "created": [
            {"id": 1, "nome_base": "Produto 1", "status_titulo_ia": "NAO_INICIADO", "status_descricao_ia": "NAO_INICIADO"},
            {"id": 2, "nome_base": "Produto 2", "status_titulo_ia": "NAO_INICIADO", "status_descricao_ia": "NAO_INICIADO"},
        ],
        "updated": [],
    }

    summary = MODULE.summarize_flow_payload(payload, sample_size=1)

    assert summary["status"] == "IMPORTED"
    assert summary["created"]["count"] == 2
    assert summary["created"]["sample"] == [
        {
            "id": 1,
            "nome_base": "Produto 1",
            "status_titulo_ia": "NAO_INICIADO",
            "status_descricao_ia": "NAO_INICIADO",
        }
    ]
    assert summary["updated"] == {"count": 0, "sample": []}


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
            "O Always a Princess Crown Frame e um porta-retrato delicado e elegante para destacar "
            "fotos infantis em ambientes decorativos, com apresentacao visual limpa e duravel."
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


def test_validate_generated_product_snapshot_flags_title_cta_and_generic_suffix():
    snapshot = {
        "status_titulo_ia": "CONCLUIDO",
        "status_descricao_ia": "CONCLUIDO",
        "titulos": [
            "Tier Displayer",
            "Exiba seus Tiers com o Tier Displayer",
            "Princess Frame Decor",
        ],
        "descricao": (
            "Produto apresentado com descricao factual, neutra e suficientemente longa para passar "
            "nas validacoes sem telefone, email, urls ou ruido comercial."
        ),
    }

    issues = MODULE.validate_generated_product_snapshot(snapshot)

    assert any(issue.startswith("titulo com CTA/promocional:") for issue in issues)
    assert any(issue.startswith("titulo com complemento generico:") for issue in issues)


def test_validate_generated_product_snapshot_flags_description_cta():
    snapshot = {
        "status_titulo_ia": "CONCLUIDO",
        "status_descricao_ia": "CONCLUIDO",
        "titulos": [
            "Tier Displayer",
            "Display Tier",
            "Tier para Display",
        ],
        "descricao": (
            "Estrutura escalonada para exposicao organizada de produtos em loja. "
            "Adquira ja e impulsione suas vendas com este display."
        ),
    }

    issues = MODULE.validate_generated_product_snapshot(snapshot)

    assert "descricao com CTA/promocional" in issues


def test_run_accepts_fornecedor_preview_with_import_file_id_only(tmp_path):
    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000",
        api_prefix="/api/v1",
        admin_email="admin@example.com",
        admin_password="password",
        catalog_url="https://example.com/catalog.pdf",
        catalog_path=str(tmp_path / "catalog.pdf"),
        supplier_name="Smoke",
        supplier_site_url="https://example.com",
        flow="fornecedores",
        product_type_id=None,
        start_page=1,
        sample_products=1,
        import_timeout_seconds=30,
        generation_timeout_seconds=30,
        report_path=str(tmp_path / "report.json"),
        keep_import=True,
        expect_no_products=False,
    )
    validator = MODULE.RealCatalogPipelineValidator(args)

    validator.ensure_backend_health = lambda: {"status": "ok"}
    validator.login = lambda: None
    validator.fetch_product_types = lambda: [{"id": 3, "attribute_templates": []}]
    validator.download_catalog = lambda: Path(args.catalog_path)
    validator.create_supplier = lambda: {"id": 77, "nome": "Smoke"}
    validator.preview_catalog = lambda supplier_id, catalog_path: {"import_file_id": 188, "total_pages": 16}

    captured: dict[str, int] = {}

    def fake_start_import(*, file_id, supplier_id, product_type_id):
        captured["start_file_id"] = file_id
        return {"job_id": 188, "status": "PROCESSING"}

    def fake_wait_for_import(*, file_id, job_id=None):
        captured["wait_file_id"] = file_id
        captured["wait_job_id"] = job_id
        return {"status": "IMPORTED", "result_summary": {"created": [{"id": 501}]}, "pages_processed": 16, "total_pages": 16}

    validator.start_import = fake_start_import
    validator.wait_for_import = fake_wait_for_import
    validator.fetch_flow_review = lambda job_id: {"job_id": job_id, "items": []}
    validator.commit_flow_review = lambda job_id: {"job_id": job_id, "auto_commit": True}
    validator.fetch_imported_products = lambda supplier_id, limit: [{"id": 501, "nome_base": "Produto Smoke"}]
    validator.trigger_generation = lambda product_id: None
    validator.wait_for_generated_product = lambda product_id: {
        "id": product_id,
        "nome_base": "Produto Smoke",
        "status_titulo_ia": "CONCLUIDO",
        "status_descricao_ia": "CONCLUIDO",
        "descricao_chat_api": (
            "Descricao longa, limpa e suficientemente detalhada para passar na validacao local sem ruido "
            "comercial, telefone, email, links externos ou qualquer boilerplate institucional desnecessario."
        ),
        "dados_brutos_web": {"titulos_sugeridos_gerados": ["Titulo 1", "Titulo 2", "Titulo 3"]},
    }

    try:
        report = validator.run()
    finally:
        validator.close()

    assert report["ok"] is True
    assert captured == {"start_file_id": 188, "wait_file_id": 188, "wait_job_id": 188}


def test_create_supplier_uses_unique_suffix_in_name_and_site(tmp_path):
    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000",
        api_prefix="/api/v1",
        admin_email="admin@example.com",
        admin_password="password",
        catalog_url="https://example.com/catalog.pdf",
        catalog_path=str(tmp_path / "catalog.pdf"),
        supplier_name="Smoke",
        supplier_site_url="https://example.com",
        flow="fornecedores",
        product_type_id=None,
        start_page=1,
        sample_products=1,
        import_timeout_seconds=30,
        generation_timeout_seconds=30,
        report_path=str(tmp_path / "report.json"),
        keep_import=True,
        expect_no_products=False,
    )
    validator = MODULE.RealCatalogPipelineValidator(args)
    validator._token = "token"

    captured: dict[str, object] = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": 77}

    class DummyClient:
        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return DummyResponse()

        def close(self):
            return None

    validator._client = DummyClient()

    try:
        supplier = validator.create_supplier()
    finally:
        validator.close()

    assert supplier == {"id": 77}
    assert captured["url"] == "http://127.0.0.1:8000/api/v1/fornecedores/"
    assert captured["headers"] == {"Authorization": "Bearer token"}
    assert str(captured["json"]["nome"]).startswith("Smoke ")
    assert "/smoke-" in str(captured["json"]["site_url"])


def test_run_accepts_expected_no_products_catalog(tmp_path):
    args = argparse.Namespace(
        base_url="http://127.0.0.1:8000",
        api_prefix="/api/v1",
        admin_email="admin@example.com",
        admin_password="password",
        catalog_url="https://example.com/catalog.pdf",
        catalog_path=str(tmp_path / "catalog.pdf"),
        supplier_name="Smoke",
        supplier_site_url="https://example.com",
        flow="fornecedores",
        product_type_id=None,
        start_page=1,
        sample_products=1,
        import_timeout_seconds=30,
        generation_timeout_seconds=30,
        report_path=str(tmp_path / "report.json"),
        keep_import=True,
        expect_no_products=True,
    )
    validator = MODULE.RealCatalogPipelineValidator(args)

    validator.ensure_backend_health = lambda: {"status": "ok"}
    validator.login = lambda: None
    validator.fetch_product_types = lambda: [{"id": 3, "attribute_templates": []}]
    validator.download_catalog = lambda: Path(args.catalog_path)
    validator.create_supplier = lambda: {"id": 91, "nome": "Smoke"}
    validator.preview_catalog = lambda supplier_id, catalog_path: {"import_file_id": 201, "total_pages": 16}
    validator.start_import = lambda file_id, supplier_id, product_type_id: {"job_id": 201, "status": "PROCESSING"}
    validator.wait_for_import = lambda file_id, job_id=None: {
        "status": "IMPORTED",
        "result_summary": {"created": []},
        "pages_processed": 16,
        "total_pages": 16,
    }
    validator.fetch_flow_review = lambda job_id: {"ignored_non_critical": [{"reason": "marketing booklet"}]}
    validator.commit_flow_review = lambda job_id: {"job_id": job_id, "auto_commit": True}
    validator.fetch_imported_products = lambda supplier_id, limit: []

    try:
        report = validator.run()
    finally:
        validator.close()

    assert report["ok"] is True
    assert report["expectation"] == "no_products"
    assert report["sample_products"] == []


