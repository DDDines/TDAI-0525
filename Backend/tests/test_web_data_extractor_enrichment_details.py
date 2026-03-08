"""Detailed coverage for web extraction enrichment workflow and OCR runtime."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from Backend import models
from Backend.testing.runtime_apis import web_extractor as web_module


class _FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0
        self.refresh_calls = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj, attribute_names=None):
        self.refresh_calls.append((obj, attribute_names))


def _produto_stub(**overrides):
    payload = {
        "id": 77,
        "status_enriquecimento_web": None,
        "dados_brutos_web": overrides.pop("dados_brutos_web", {}),
        "log_enriquecimento_web": None,
        "fornecedor": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_web_extraction_enrichment_helper_methods_cover_status_branches():
    runtime = SimpleNamespace(now_iso=lambda: "2026-03-08T00:00:00+00:00")
    workflow = web_module.WebExtractionEnrichmentWorkflow(
        db=_FakeDb(),
        url="https://example.com/p",
        produto=_produto_stub(dados_brutos_web={"marca": "Original", "sku": "123"}),
        runtime=runtime,
    )

    workflow._merge_metadata({"marca": None, "nome": "Produto X", "sku": "SKU-1"})
    assert workflow.produto.dados_brutos_web == {
        "marca": "Original",
        "sku": "SKU-1",
        "nome": "Produto X",
    }

    assert workflow._define_status_final(dados_normalizados_de_meta={}, texto_principal=None) == models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
    assert workflow._define_status_final(dados_normalizados_de_meta={}, texto_principal="texto") == models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
    assert workflow._define_status_final(dados_normalizados_de_meta={"nome": "Produto"}, texto_principal="texto") == models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
    assert [entry["level"] for entry in workflow.log_enriquecimento[-3:]] == ["WARNING", "INFO", "INFO"]


@pytest.mark.asyncio
async def test_web_extraction_enrichment_workflow_run_failure_and_success_paths():
    class MissingHtmlRuntime:
        def now_iso(self):
            return "2026-03-08T00:00:00+00:00"

        async def collect_html(self, *, url):
            return None

    db_fail = _FakeDb()
    produto_fail = _produto_stub(dados_brutos_web={})
    failed = await web_module.WebExtractionEnrichmentWorkflow(
        db=db_fail,
        url="https://example.com/fail",
        produto=produto_fail,
        runtime=MissingHtmlRuntime(),
    ).run()
    assert failed is produto_fail
    assert produto_fail.status_enriquecimento_web == models.StatusEnriquecimentoEnum.FALHOU
    assert produto_fail.log_enriquecimento_web[-1]["level"] == "ERROR"
    assert db_fail.commits == 2
    assert db_fail.refresh_calls == [(produto_fail, None)]

    class PartialRuntime:
        def now_iso(self):
            return "2026-03-08T00:00:00+00:00"

        async def collect_html(self, *, url):
            return "<html>texto</html>"

        def extract_main_text(self, *, html_content):
            return "texto principal util"

        def extract_structured_metadata(self, *, html_content, url):
            return {}

        def normalize_metadata(self, *, metadata):
            return {}

    db_partial = _FakeDb()
    produto_partial = _produto_stub(dados_brutos_web=None)
    partial = await web_module.WebExtractionEnrichmentWorkflow(
        db=db_partial,
        url="https://example.com/partial",
        produto=produto_partial,
        runtime=PartialRuntime(),
    ).run()
    assert partial.status_enriquecimento_web == models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
    assert partial.dados_brutos_web["texto_pagina_extraido"] == "texto principal util"
    assert db_partial.commits == 2
    assert db_partial.refresh_calls[-1] == (produto_partial, ["fornecedor"])

    class SuccessRuntime(PartialRuntime):
        def extract_structured_metadata(self, *, html_content, url):
            return {"json-ld_product_candidate": {"name": "Produto Y"}}

        def normalize_metadata(self, *, metadata):
            return {"nome": "Produto Y", "marca": "Marca Y"}

    db_success = _FakeDb()
    produto_success = _produto_stub(dados_brutos_web={"sku": "SKU-9"})
    success = await web_module.WebExtractionEnrichmentWorkflow(
        db=db_success,
        url="https://example.com/success",
        produto=produto_success,
        runtime=SuccessRuntime(),
    ).run()
    assert success.status_enriquecimento_web == models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
    assert success.dados_brutos_web["nome"] == "Produto Y"
    assert success.dados_brutos_web["marca"] == "Marca Y"
    assert success.dados_brutos_web["sku"] == "SKU-9"
    assert db_success.commits == 2


def test_web_extraction_enrichment_runtime_and_url_engine_delegate():
    calls = {}

    class FakeContentWorkflow:
        async def coletar_conteudo_pagina_playwright(self, url):
            calls["collect"] = url
            return f"html:{url}"

    class FakeSupportWorkflow:
        def extrair_texto_principal_com_trafilatura(self, html_content):
            calls["text"] = html_content
            return f"text:{html_content}"

        def extrair_metadados_estruturados(self, html_content, url):
            calls["meta"] = (html_content, url)
            return {"meta": url}

        def normalizar_dados_de_metadados(self, metadata_bruta):
            calls["normalize"] = metadata_bruta
            return {"normalized": metadata_bruta}

    runtime = web_module.WebExtractionEnrichmentRuntime(
        content_collection_workflow=FakeContentWorkflow(),
        extraction_support_workflow=FakeSupportWorkflow(),
    )

    assert runtime.now_iso().endswith("+00:00")

    import asyncio

    assert asyncio.run(runtime.collect_html(url="https://example.com")) == "html:https://example.com"
    assert runtime.extract_main_text(html_content="<html>") == "text:<html>"
    assert runtime.extract_structured_metadata(html_content="<html>", url="https://example.com") == {"meta": "https://example.com"}
    assert runtime.normalize_metadata(metadata={"x": 1}) == {"normalized": {"x": 1}}

    class FakeWorkflow:
        def __init__(self, *, db, url, produto):
            calls["workflow_init"] = (db, url, produto)

        async def run(self):
            return "produto-atualizado"

    original_workflow = web_module.WebExtractionEnrichmentWorkflow
    web_module.WebExtractionEnrichmentWorkflow = FakeWorkflow
    try:
        engine = web_module.WebURLExtractionEngineRuntime()
        assert asyncio.run(engine.extract_relevant_data_from_url(db="db", url="https://example.com/p", produto="produto")) == "produto-atualizado"
    finally:
        web_module.WebExtractionEnrichmentWorkflow = original_workflow

    assert calls["collect"] == "https://example.com"
    assert calls["workflow_init"] == ("db", "https://example.com/p", "produto")


def test_web_ocr_engine_runtime_success_and_http_exception_paths(monkeypatch):
    runtime = web_module.WebOCREngineRuntime()
    google_module = ModuleType("google")
    cloud_module = ModuleType("google.cloud")

    class FakeResponse:
        def __init__(self, message=""):
            self.error = SimpleNamespace(message=message)
            self.full_text_annotation = {"text": "ok"}

    class FakeVision:
        class ImageAnnotatorClient:
            def __init__(self, response_message=""):
                self._response_message = response_message

            def document_text_detection(self, image):
                _ = image
                return FakeResponse(self._response_message)

        class Image:
            def __init__(self, content):
                self.content = content

    cloud_module.vision = FakeVision
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)

    assert runtime.extract_text_from_image_region(b"img") == {"text": "ok"}

    class FailingVision(FakeVision):
        class ImageAnnotatorClient:
            def document_text_detection(self, image):
                _ = image
                return FakeResponse("vision failed")

    cloud_module.vision = FailingVision
    with pytest.raises(web_module.HTTPException) as exc:
        runtime.extract_text_from_image_region(b"img")
    assert exc.value.status_code == 500
