"""Coverage for web data extractor runtime/workflow composition wrappers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor


def test_web_extraction_support_runtime_apply_overrides_and_workflow_delegate():
    metadata_runtime = SimpleNamespace(
        extrair_texto_principal_com_trafilatura=lambda html: f"text:{html}",
        extrair_metadados_estruturados=lambda html_content, url: {"meta": (html_content, url)},
        normalizar_dados_de_metadados=lambda metadata_bruta: {"normalized": metadata_bruta},
    )
    llm_runtime = SimpleNamespace(
        extrair_dados_produto_com_llm=lambda **kwargs: None,
    )
    enrichment_runtime = SimpleNamespace(
        extract_relevant_data_from_url=lambda **kwargs: None,
    )
    ocr_runtime = SimpleNamespace(extract_text_from_image_region=lambda image_bytes: {"ocr": image_bytes})

    runtime = web_extractor.WebExtractionSupportRuntime(
        metadata_runtime=metadata_runtime,
        llm_runtime=llm_runtime,
        enrichment_runtime=enrichment_runtime,
        ocr_runtime=ocr_runtime,
    )
    override = SimpleNamespace(
        metadata_runtime=SimpleNamespace(
            extrair_texto_principal_com_trafilatura=lambda html: f"override:{html}",
            extrair_metadados_estruturados=lambda html_content, url: {"override_meta": (html_content, url)},
            normalizar_dados_de_metadados=lambda metadata_bruta: {"override_normalized": metadata_bruta},
        ),
        llm_runtime=SimpleNamespace(
            extrair_dados_produto_com_llm=lambda **kwargs: {"llm": kwargs["produto_nome_base"]},
        ),
        enrichment_runtime=SimpleNamespace(
            extract_relevant_data_from_url=lambda **kwargs: {"url": kwargs["url"]},
        ),
        ocr_runtime=SimpleNamespace(extract_text_from_image_region=lambda image_bytes: {"override_ocr": image_bytes}),
    )

    assert runtime.apply_overrides(override) is runtime

    workflow = web_extractor.WebExtractionSupportWorkflow(runtime=runtime)
    assert workflow.extrair_texto_principal_com_trafilatura("<html>") == "override:<html>"
    assert workflow.extrair_metadados_estruturados("<html>", "https://example.com") == {"override_meta": ("<html>", "https://example.com")}
    assert workflow.normalizar_dados_de_metadados({"x": 1}) == {"override_normalized": {"x": 1}}
    assert workflow.extract_text_from_image_region(b"img") == {"override_ocr": b"img"}


@pytest.mark.asyncio
async def test_web_extraction_support_workflow_async_and_runtime_wrappers_delegate():
    class FakeLlmRuntime:
        async def extrair_dados_produto_com_llm(self, **kwargs):
            return {"llm": kwargs["produto_nome_base"], "user": kwargs["user"]}

    class FakeEnrichmentRuntime:
        async def extract_relevant_data_from_url(self, **kwargs):
            return {"produto": kwargs["produto"], "url": kwargs["url"], "db": kwargs["db"]}

    workflow = web_extractor.WebExtractionSupportWorkflow(
        metadata_runtime=SimpleNamespace(
            extrair_texto_principal_com_trafilatura=lambda html: html,
            extrair_metadados_estruturados=lambda html_content, url: {"meta": url},
            normalizar_dados_de_metadados=lambda metadata_bruta: metadata_bruta,
        ),
        llm_runtime=FakeLlmRuntime(),
        enrichment_runtime=FakeEnrichmentRuntime(),
        ocr_runtime=SimpleNamespace(extract_text_from_image_region=lambda image_bytes: image_bytes),
    )

    assert await workflow.extrair_dados_produto_com_llm(
        texto_pagina="texto",
        metadados_normalizados={"nome": "Produto"},
        campos_desejados=["nome"],
        produto_nome_base="Produto",
        user="user-1",
    ) == {"llm": "Produto", "user": "user-1"}
    assert await workflow.extract_relevant_data_from_url(db="db", url="https://example.com", produto="produto") == {
        "produto": "produto",
        "url": "https://example.com",
        "db": "db",
    }

    class FakeEngine:
        async def extrair_dados_produto_com_llm(self, **kwargs):
            return {"engine": kwargs["produto_nome_base"]}

    class FakeUrlEngine:
        async def extract_relevant_data_from_url(self, **kwargs):
            return {"url_engine": kwargs["url"]}

    class FakeOcrEngine:
        def extract_text_from_image_region(self, *, image_bytes):
            return {"ocr_engine": image_bytes}

    llm_runtime = web_extractor.WebLLMExtractionRuntime(engine_runtime=FakeEngine())
    url_runtime = web_extractor.WebURLExtractionRuntime(engine_runtime=FakeUrlEngine())
    ocr_runtime = web_extractor.WebOCRRuntime(engine_runtime=FakeOcrEngine())

    assert await llm_runtime.extrair_dados_produto_com_llm(texto_pagina="texto", produto_nome_base="Produto X") == {"engine": "Produto X"}
    assert await url_runtime.extract_relevant_data_from_url(db="db", url="https://example.com/p", produto="produto") == {"url_engine": "https://example.com/p"}
    assert ocr_runtime.extract_text_from_image_region(b"img") == {"ocr_engine": b"img"}


def test_web_data_extractor_runtime_builds_defaults_with_fakes(monkeypatch):
    created = {}

    class FakeSearchEngineRuntime:
        def __init__(self):
            created["search_engine"] = self

    class FakeContentFetchEngineRuntime:
        def __init__(self, *, search_runtime):
            created["content_fetch"] = search_runtime
            self.flags = []

        def set_playwright_chromium_indisponivel(self, value):
            self.flags.append(value)

    class FakeMetadataExtractionRuntime:
        def __init__(self):
            created["metadata"] = self

    class FakeWebLLMExtractionEngineRuntime:
        def __init__(self):
            created["llm_engine"] = self

    class FakeWebURLExtractionEngineRuntime:
        def __init__(self):
            created["url_engine"] = self

    class FakeWebOCREngineRuntime:
        def __init__(self):
            created["ocr_engine"] = self

    class FakeWebSearchRuntime:
        def __init__(self, *, engine_runtime):
            created["search_runtime"] = engine_runtime

    class FakeWebSearchWorkflow:
        def __init__(self, *, runtime):
            created["search_workflow"] = runtime

    class FakeWebContentCollectionRuntime:
        def __init__(self, *, engine_runtime):
            created["content_runtime"] = engine_runtime

    class FakeWebContentCollectionWorkflow:
        def __init__(self, *, runtime):
            created["content_workflow"] = runtime

    class FakeWebLLMExtractionRuntime:
        def __init__(self, *, engine_runtime):
            created["llm_runtime"] = engine_runtime

    class FakeWebURLExtractionRuntime:
        def __init__(self, *, engine_runtime):
            created["url_runtime"] = engine_runtime

    class FakeWebOCRRuntime:
        def __init__(self, *, engine_runtime):
            created["ocr_runtime"] = engine_runtime

    class FakeWebExtractionSupportWorkflow:
        def __init__(self, **kwargs):
            created["support_workflow"] = kwargs

    monkeypatch.setattr(web_extractor, "WebSearchEngineRuntime", FakeSearchEngineRuntime)
    monkeypatch.setattr(web_extractor, "WebContentFetchEngineRuntime", FakeContentFetchEngineRuntime)
    monkeypatch.setattr(web_extractor, "MetadataExtractionRuntime", FakeMetadataExtractionRuntime)
    monkeypatch.setattr(web_extractor, "WebLLMExtractionEngineRuntime", FakeWebLLMExtractionEngineRuntime)
    monkeypatch.setattr(web_extractor, "WebURLExtractionEngineRuntime", FakeWebURLExtractionEngineRuntime)
    monkeypatch.setattr(web_extractor, "WebOCREngineRuntime", FakeWebOCREngineRuntime)
    monkeypatch.setattr(web_extractor, "WebSearchRuntime", FakeWebSearchRuntime)
    monkeypatch.setattr(web_extractor, "WebSearchWorkflow", FakeWebSearchWorkflow)
    monkeypatch.setattr(web_extractor, "WebContentCollectionRuntime", FakeWebContentCollectionRuntime)
    monkeypatch.setattr(web_extractor, "WebContentCollectionWorkflow", FakeWebContentCollectionWorkflow)
    monkeypatch.setattr(web_extractor, "WebLLMExtractionRuntime", FakeWebLLMExtractionRuntime)
    monkeypatch.setattr(web_extractor, "WebURLExtractionRuntime", FakeWebURLExtractionRuntime)
    monkeypatch.setattr(web_extractor, "WebOCRRuntime", FakeWebOCRRuntime)
    monkeypatch.setattr(web_extractor, "WebExtractionSupportWorkflow", FakeWebExtractionSupportWorkflow)

    runtime = web_extractor.WebDataExtractorRuntime(playwright_chromium_indisponivel=True)

    assert created["content_fetch"] is created["search_engine"]
    assert created["support_workflow"]["metadata_runtime"] is created["metadata"]
    assert created["support_workflow"]["llm_runtime"].__class__ is FakeWebLLMExtractionRuntime
    assert created["support_workflow"]["enrichment_runtime"].__class__ is FakeWebURLExtractionRuntime
    assert created["support_workflow"]["ocr_runtime"].__class__ is FakeWebOCRRuntime
    assert runtime._content_fetch_engine_runtime.flags == [True]


@pytest.mark.asyncio
async def test_web_data_extractor_runtime_properties_and_delegates():
    class FakeSearchWorkflow:
        def busca_publica_disponivel(self):
            return True

        async def buscar_urls_publicas(self, **kwargs):
            return [f"public:{kwargs['query']}:{kwargs['num_results']}"]

        async def buscar_urls_google(self, **kwargs):
            return [f"google:{kwargs['query']}:{kwargs['num_results']}"]

    class FakeContentWorkflow:
        async def coletar_conteudo_pagina_playwright(self, url):
            return f"html:{url}"

    class FakeSupportWorkflow:
        def extrair_texto_principal_com_trafilatura(self, html_content):
            return f"text:{html_content}"

        def extrair_metadados_estruturados(self, html_content, url):
            return {"meta": (html_content, url)}

        def normalizar_dados_de_metadados(self, metadata_bruta):
            return {"normalized": metadata_bruta}

        async def extrair_dados_produto_com_llm(self, **kwargs):
            return {"llm": kwargs["produto_nome_base"]}

        async def extract_relevant_data_from_url(self, **kwargs):
            return {"session": kwargs["db"], "url": kwargs["url"], "produto": kwargs["produto"]}

        def extract_text_from_image_region(self, image_bytes):
            return {"ocr": image_bytes}

    runtime = web_extractor.WebDataExtractorRuntime(
        search_engine_runtime=SimpleNamespace(),
        content_fetch_engine_runtime=SimpleNamespace(set_playwright_chromium_indisponivel=lambda value: None),
        metadata_extraction_runtime=SimpleNamespace(),
        llm_extraction_engine_runtime=SimpleNamespace(),
        url_extraction_engine_runtime=SimpleNamespace(),
        ocr_engine_runtime=SimpleNamespace(),
        search_workflow=FakeSearchWorkflow(),
        content_collection_workflow=FakeContentWorkflow(),
        extraction_support_workflow=FakeSupportWorkflow(),
    )

    assert runtime.search_workflow.__class__ is FakeSearchWorkflow
    assert runtime.content_collection_workflow.__class__ is FakeContentWorkflow
    assert runtime.extraction_support_workflow.__class__ is FakeSupportWorkflow
    assert runtime.busca_publica_disponivel() is True
    assert await runtime.buscar_urls_publicas(query="peca", num_results=2) == ["public:peca:2"]
    assert await runtime.buscar_urls_google(query="peca", num_results=1) == ["google:peca:1"]
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com") == "html:https://example.com"
    assert runtime.extrair_texto_principal_com_trafilatura("<html>") == "text:<html>"
    assert runtime.extrair_metadados_estruturados("<html>", "https://example.com") == {"meta": ("<html>", "https://example.com")}
    assert runtime.normalizar_dados_de_metadados({"a": 1}) == {"normalized": {"a": 1}}
    assert await runtime.extrair_dados_produto_com_llm(texto_pagina="texto", produto_nome_base="Produto") == {"llm": "Produto"}
    assert await runtime.extract_relevant_data_from_url(session="db", url="https://example.com/p", produto="produto") == {
        "session": "db",
        "url": "https://example.com/p",
        "produto": "produto",
    }
    assert runtime.extract_text_from_image_region(b"img") == {"ocr": b"img"}
