"""Focused internals coverage for web data extractor runtime module."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor as web_module


class _UrlOpenResponse:
    """Simple urlopen response stub."""

    def __init__(self, body: str, content_type: str = "text/html"):
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _AiWorkflowStub:
    """AI workflow stub used by LLM extraction tests."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def call_openai_api(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class _TopLevelFunctionSurface:
    """Represent top level function surface and centralize responsibilities for this module."""

    @pytest.mark.asyncio
    async def test_web_search_engine_cache_and_google_fallback_paths(monkeypatch):
        """Cover cache hit/miss, Google CSE success and public fallback."""
        runtime = web_module.WebSearchEngineRuntime()
        await runtime.search_cache_set("abc", ["https://cached"])
        assert await runtime.search_cache_get("abc") == ["https://cached"]

        runtime._search_cache["old"] = (0.0, ["https://expired"])
        runtime._search_cache_ttl_seconds = 0.1
        assert await runtime.search_cache_get("old") is None

        monkeypatch.setattr(web_module, "GOOGLE_API_CLIENT_INSTALLED", True)
        monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_API_KEY", "key", raising=False)
        monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_ID", "cx", raising=False)
        monkeypatch.setattr(
            runtime,
            "_executar_busca_google_cse",
            lambda query_limpa, limite: [
                "https://example.com/produto",
                "https://loja.com/item",
            ],
        )

        urls = await runtime.buscar_urls_google_async("produto x", num_results=2)
        assert urls == ["https://example.com/produto", "https://loja.com/item"]

        monkeypatch.setattr(web_module, "GOOGLE_API_CLIENT_INSTALLED", False)
        monkeypatch.setattr(
            runtime,
            "buscar_urls_publicas_async",
            lambda query, num_results=3: asyncio.sleep(0, result=["https://fallback.com/item"]),
        )
        urls = await runtime.buscar_urls_google_async("produto y", num_results=1)
        assert urls == ["https://fallback.com/item"]
        assert await runtime.search_cache_get("produto y") == ["https://fallback.com/item"]

    def test_web_search_engine_url_scoring_normalization_and_sync_search(monkeypatch):
        """Cover URL scoring, redirect unwrapping and public search parsing."""
        runtime = web_module.WebSearchEngineRuntime()

        assert runtime.score_url_publica("https://amazon.com/produto/x") > 0
        assert runtime.score_url_publica("https://duckduckgo.com/?uddg=x&utm_source=a") < 0
        assert runtime.extract_redirect_destination("uddg=https%3A%2F%2Fexample.com%2Fa") == "https://example.com/a"
        assert runtime.unwrap_redirect_url(
            "https://duckduckgo.com/?uddg=https%3A%2F%2Fexample.com%2Fdest"
        ) == "https://example.com/dest"
        assert runtime.url_deve_ser_ignorada_antes_da_coleta("ftp://server/file") is True
        assert runtime.url_deve_ser_ignorada_antes_da_coleta("https://example.com/file.pdf") is True
        assert runtime.normalizar_url_busca("/produto/1", "https://loja.com/base") == "https://loja.com/produto/1"
        assert runtime.normalizar_url_busca(
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fp",
            "https://duckduckgo.com",
        ) == "https://example.com/p"
        assert runtime.normalizar_url_busca(
            "https://www.google.com/search?q=produto",
            "https://www.google.com",
        ) is None

        responses = iter(
            [
                _UrlOpenResponse('<a class="result__a" href="https://example.com/a">A</a>'),
            ]
        )
        monkeypatch.setattr(web_module, "urlopen", lambda req, timeout=8: next(responses))
        urls = runtime.buscar_urls_publicas_sync("produto teste", num_results=1)
        assert urls == ["https://example.com/a"]

    @pytest.mark.asyncio
    async def test_content_fetch_engine_covers_http_and_playwright_fallbacks(monkeypatch):
        """Cover ignored URL, direct HTTP helper and Playwright fallbacks."""
        search_runtime = SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: url.endswith(".pdf"))
        runtime = web_module.WebContentFetchEngineRuntime(search_runtime=search_runtime)

        monkeypatch.setattr(
            web_module,
            "urlopen",
            lambda req, timeout=20: _UrlOpenResponse("<html>ok</html>", "text/html; charset=utf-8"),
        )
        assert runtime.coletar_conteudo_pagina_http_sync("https://example.com") == "<html>ok</html>"

        monkeypatch.setattr(
            web_module,
            "urlopen",
            lambda req, timeout=20: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        assert await runtime.coletar_conteudo_pagina_http("https://example.com") is None
        assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/file.pdf") is None

        runtime = web_module.WebContentFetchEngineRuntime(
            search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
        )
        runtime.set_playwright_chromium_indisponivel(True)
        monkeypatch.setattr(runtime, "coletar_conteudo_pagina_http", lambda url: asyncio.sleep(0, result="http-fallback"))
        assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/a") == "http-fallback"

        runtime = web_module.WebContentFetchEngineRuntime(
            search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
        )
        monkeypatch.setattr(web_module.sys, "platform", "linux")
        async def raise_timeout(url):
            raise web_module.PlaywrightTimeoutError("timeout")

        monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_timeout)
        monkeypatch.setattr(runtime, "coletar_conteudo_pagina_http", lambda url: asyncio.sleep(0, result="http-after-timeout"))
        assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/b") == "http-after-timeout"

        runtime = web_module.WebContentFetchEngineRuntime(
            search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
        )
        async def raise_missing_browser(url):
            raise RuntimeError("Executable doesn't exist")

        monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_missing_browser)
        monkeypatch.setattr(runtime, "coletar_conteudo_pagina_http", lambda url: asyncio.sleep(0, result="http-after-error"))
        assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/c") == "http-after-error"
        assert runtime.is_playwright_chromium_indisponivel() is True

    def test_metadata_extraction_runtime_covers_normalization_and_structured_sources(monkeypatch):
        """Cover metadata cleanup, extraction and normalization from structured payloads."""
        runtime = web_module.MetadataExtractionRuntime()

        assert runtime.limpar_valor_metadado("  valor   x  ") == "valor x"
        assert runtime.limpar_valor_metadado([" a ", "", None]) == ["a"]
        assert runtime._get_first_string(["", "ok"]) == "ok"

        monkeypatch.setattr(
            web_module.extruct,
            "extract",
            lambda html, base_url, syntaxes, uniform: {
                "json-ld": [
                    {
                        "@type": "Product",
                        "name": "Reservatorio",
                        "description": "Descricao",
                        "image": [{"url": "https://img"}],
                        "brand": {"name": "Master"},
                        "sku": "SKU-1",
                        "offers": {"price": "10", "priceCurrency": "BRL", "availability": "https://schema.org/InStock"},
                    }
                ],
                "microdata": [{"properties": {"name": "Micro Nome", "brand": "Micro Marca"}}],
                "opengraph": [{"og:title": "OG Nome", "og:description": "OG Desc", "og:image": "https://og", "og:type": "product", "product:brand": "OG Marca"}],
            },
        )

        raw = runtime.extrair_metadados_estruturados("<html></html>", "https://example.com")
        normalized = runtime.normalizar_dados_de_metadados(raw)
        assert normalized["nome"] == "Reservatorio"
        assert normalized["descricao_curta"] == "Descricao"
        assert normalized["imagem_url"] == "https://img"
        assert normalized["marca"] == "Master"
        assert normalized["sku"] == "SKU-1"
        assert normalized["preco"] == "10"
        assert normalized["moeda_preco"] == "BRL"
        assert normalized["disponibilidade"] == "InStock"

        monkeypatch.setattr(
            web_module.extruct,
            "extract",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad metadata")),
        )
        assert runtime.extrair_metadados_estruturados("<html></html>", "https://example.com") == {}

    @pytest.mark.asyncio
    async def test_web_llm_extraction_engine_covers_key_paths(monkeypatch):
        """Cover empty input, missing key, success and parser error branches."""
        monkeypatch.setattr(web_module.settings, "OPENAI_API_KEY", None, raising=False)
        runtime = web_module.WebLLMExtractionEngineRuntime(ai_provider_workflow_factory=lambda: _AiWorkflowStub(response="{}"))
        assert "erro_llm" in await runtime.extrair_dados_produto_com_llm(None, None)
        missing_key = await runtime.extrair_dados_produto_com_llm("texto", {}, produto_nome_base="Produto")
        assert "erro_llm" in missing_key
        assert "OpenAI" in missing_key["erro_llm"]

        monkeypatch.setattr(web_module.settings, "OPENAI_API_KEY", "sk-test-12345678901234567890", raising=False)
        workflow = _AiWorkflowStub(response='{"marca":"Master","sku":"SKU-1"}')
        runtime = web_module.WebLLMExtractionEngineRuntime(ai_provider_workflow_factory=lambda: workflow)
        result = await runtime.extrair_dados_produto_com_llm(
            "texto principal",
            {"nome": "Reservatorio"},
            ["marca", "sku"],
            "Reservatorio",
        )
        assert result["nome"] == "Reservatorio"
        assert result["marca"] == "Master"
        assert result["sku"] == "SKU-1"
        assert workflow.calls[0]["model"] == "gpt-3.5-turbo-0125"

        runtime = web_module.WebLLMExtractionEngineRuntime(
            ai_provider_workflow_factory=lambda: _AiWorkflowStub(response="nao-json")
        )
        result = await runtime.extrair_dados_produto_com_llm("texto", {"nome": "x"}, ["nome"], "Produto")
        assert "extracao_bruta_llm_com_erro_json" in result

        runtime = web_module.WebLLMExtractionEngineRuntime(
            ai_provider_workflow_factory=lambda: _AiWorkflowStub(error=ValueError("quota"))
        )
        assert (await runtime.extrair_dados_produto_com_llm("texto", {"nome": "x"}, ["nome"], "Produto"))["erro_llm"] == "quota"

        runtime = web_module.WebLLMExtractionEngineRuntime(
            ai_provider_workflow_factory=lambda: _AiWorkflowStub(error=RuntimeError("boom"))
        )
        assert (await runtime.extrair_dados_produto_com_llm("texto", {"nome": "x"}, ["nome"], "Produto"))["erro_llm_inesperado"] == "boom"


test_web_search_engine_cache_and_google_fallback_paths = (
    _TopLevelFunctionSurface.test_web_search_engine_cache_and_google_fallback_paths
)
test_web_search_engine_url_scoring_normalization_and_sync_search = (
    _TopLevelFunctionSurface.test_web_search_engine_url_scoring_normalization_and_sync_search
)
test_content_fetch_engine_covers_http_and_playwright_fallbacks = (
    _TopLevelFunctionSurface.test_content_fetch_engine_covers_http_and_playwright_fallbacks
)
test_metadata_extraction_runtime_covers_normalization_and_structured_sources = (
    _TopLevelFunctionSurface.test_metadata_extraction_runtime_covers_normalization_and_structured_sources
)
test_web_llm_extraction_engine_covers_key_paths = (
    _TopLevelFunctionSurface.test_web_llm_extraction_engine_covers_key_paths
)
