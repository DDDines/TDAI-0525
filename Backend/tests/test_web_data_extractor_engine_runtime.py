from __future__ import annotations

import pytest

import Backend.services.web_data_extractor_service as web_extractor


@pytest.mark.asyncio
async def test_web_search_runtime_delega_para_engine_runtime():
    calls = []

    class FakeEngine:
        async def buscar_urls_publicas_async(self, *, query: str, num_results: int):
            calls.append(("public", query, num_results))
            return ["https://example.com/public"]

        async def buscar_urls_google_async(self, *, query: str, num_results: int):
            calls.append(("google", query, num_results))
            return ["https://example.com/google"]

    runtime = web_extractor._WebSearchRuntime(engine_runtime=FakeEngine())

    public_urls = await runtime.buscar_urls_publicas_async(
        query="peca",
        num_results=2,
    )
    google_urls = await runtime.buscar_urls_google_async(
        query="peca",
        num_results=1,
    )

    assert public_urls == ["https://example.com/public"]
    assert google_urls == ["https://example.com/google"]
    assert calls == [("public", "peca", 2), ("google", "peca", 1)]


@pytest.mark.asyncio
async def test_web_content_runtime_delega_para_engine_runtime():
    calls = []

    class FakeEngine:
        async def coletar_conteudo_pagina_playwright_impl(self, url: str):
            calls.append(url)
            return "<html>ok</html>"

    runtime = web_extractor._WebContentCollectionRuntime(engine_runtime=FakeEngine())

    html = await runtime.coletar_conteudo_pagina_playwright("https://example.com/p")

    assert html == "<html>ok</html>"
    assert calls == ["https://example.com/p"]


def test_wrappers_busca_delegam_para_runtime_global(monkeypatch):
    class FakeSearchEngine:
        def busca_publica_disponivel(self):
            return False

        def url_deve_ser_ignorada_antes_da_coleta(self, url: str):
            return url.endswith(".tmp")

        def normalizar_url_busca(self, candidata: str, base_url: str):
            return f"{base_url}|{candidata}"

    monkeypatch.setattr(
        web_extractor,
        "_web_search_engine_runtime",
        FakeSearchEngine(),
    )

    assert web_extractor.busca_publica_disponivel() is False
    assert web_extractor._url_deve_ser_ignorada_antes_da_coleta("x.tmp") is True
    assert (
        web_extractor._normalizar_url_busca("item", "https://base")
        == "https://base|item"
    )


@pytest.mark.asyncio
async def test_web_llm_runtime_delega_para_engine_runtime():
    called = {}

    class FakeEngine:
        async def extrair_dados_produto_com_llm_impl(self, **kwargs):
            called.update(kwargs)
            return {"nome_base": "Produto X"}

    runtime = web_extractor._WebLLMExtractionRuntime(engine_runtime=FakeEngine())
    result = await runtime.extrair_dados_produto_com_llm(
        texto_pagina="texto",
        produto_nome_base="Produto X",
    )

    assert result == {"nome_base": "Produto X"}
    assert called["produto_nome_base"] == "Produto X"


@pytest.mark.asyncio
async def test_web_url_runtime_delega_para_engine_runtime():
    called = {}

    class FakeEngine:
        async def extract_relevant_data_from_url_impl(self, **kwargs):
            called.update(kwargs)
            return kwargs["produto"]

    runtime = web_extractor._WebURLExtractionRuntime(engine_runtime=FakeEngine())
    produto = object()
    returned = await runtime.extract_relevant_data_from_url(
        db="db",
        url="https://example.com/p",
        produto=produto,
    )

    assert returned is produto
    assert called["url"] == "https://example.com/p"


def test_web_ocr_runtime_delega_para_engine_runtime():
    called = {}

    class FakeEngine:
        def extract_text_from_image_region_impl(self, image_bytes: bytes):
            called["image_bytes"] = image_bytes
            return {"text": "ok"}

    runtime = web_extractor._WebOCRRuntime(engine_runtime=FakeEngine())
    result = runtime.extract_text_from_image_region(b"img")

    assert result == {"text": "ok"}
    assert called["image_bytes"] == b"img"
