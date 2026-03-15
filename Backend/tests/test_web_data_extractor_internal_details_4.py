from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor as web_module


class _UrlOpenResponse:
    def __init__(self, body: str, content_type: str = "text/html"):
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_search_runtime_covers_remaining_url_normalization_and_async_branches(monkeypatch):
    runtime = web_module.WebSearchEngineRuntime()

    destinations = iter(
        [
            "https://example.com/redirect-1",
            "https://example.com/redirect-2",
            "https://example.com/redirect-3",
        ]
    )
    runtime.extract_redirect_destination = lambda query: next(destinations)
    assert runtime.unwrap_redirect_url("https://tracker.com/?u=a", max_hops=3) == (
        "https://example.com/redirect-3"
    )

    runtime = web_module.WebSearchEngineRuntime()
    assert runtime.url_deve_ser_ignorada_antes_da_coleta(
        "https://facebook.com/l.php?url=https%3A%2F%2Fexample.com%2Fp"
    ) is True

    assert (
        runtime.normalizar_url_busca(
            "https://facebook.com/l.php?utm_source=x&url=https%3A%2F%2Fexample.com%2Fp",
            "https://base",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://duckduckgo.com/l/?uddg=&u=https%3A%2F%2Fduckduckgo.com%2Fredirect",
            "https://duckduckgo.com/html/?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://www.bing.com/aclick?x=1",
            "https://www.bing.com/search?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://www.google.com/search?q=produto",
            "https://www.google.com",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://example.com/p?utm_campaign=abc",
            "https://base",
        )
        is None
    )
    assert runtime.normalizar_url_busca("https:///sem-host", "https://base") is None

    monkeypatch.setattr(
        runtime,
        "buscar_urls_publicas_sync",
        lambda query, num_results=3: [f"{query}:{num_results}"],
    )
    assert await runtime.buscar_urls_publicas_async("produto", num_results=2) == ["produto:2"]


@pytest.mark.asyncio
async def test_search_runtime_covers_missing_google_config_and_metadata_branches(monkeypatch):
    runtime = web_module.WebSearchEngineRuntime()
    monkeypatch.setattr(web_module, "GOOGLE_API_CLIENT_INSTALLED", True)
    monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_API_KEY", "", raising=False)
    monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_ID", "", raising=False)
    monkeypatch.setattr(
        runtime,
        "buscar_urls_publicas_async",
        lambda query, num_results=3: asyncio.sleep(0, result=["https://fallback/item"]),
    )
    assert await runtime.buscar_urls_google_async("produto sem cse", num_results=1) == [
        "https://fallback/item"
    ]

    metadata_runtime = web_module.MetadataExtractionRuntime()
    monkeypatch.setattr(
        web_module.extruct,
        "extract",
        lambda *args, **kwargs: {"opengraph": [{"og:title": "Produto OG"}]},
    )
    extracted = metadata_runtime.extrair_metadados_estruturados(
        "<html></html>",
        "https://example.com/p",
    )
    assert extracted["opengraph"] == {"og:title": "Produto OG"}

    normalized = metadata_runtime.normalizar_dados_de_metadados(
        {"json-ld_product_candidate": {"name": "Produto", "offers": "nao-dict"}}
    )
    assert normalized["nome"] == "Produto"
    assert "preco" not in normalized


@pytest.mark.asyncio
async def test_fetch_runtime_covers_thread_loop_and_playwright_fallback_logging(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )

    created_loop = SimpleNamespace(
        run_until_complete=lambda coro: (getattr(coro, "close", lambda: None)(), "thread-html")[1],
        shutdown_asyncgens=lambda: SimpleNamespace(close=lambda: None),
        close=lambda: None,
    )
    monkeypatch.setattr(web_module.sys, "platform", "linux")
    monkeypatch.setattr(web_module.asyncio, "new_event_loop", lambda: created_loop)
    monkeypatch.setattr(web_module.asyncio, "set_event_loop", lambda loop: None)
    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", lambda url: asyncio.sleep(0, result=f"pw:{url}"))
    assert runtime.coletar_conteudo_playwright_em_thread_sync("https://example.com/linux") == "thread-html"

    class _SelectorLoop:
        pass

    monkeypatch.setattr(web_module.sys, "platform", "win32")
    monkeypatch.setattr(web_module.asyncio, "get_running_loop", lambda: _SelectorLoop())

    async def raise_missing_browser(fn, *args):
        _ = fn, args
        raise RuntimeError("Executable doesn't exist\nmissing browser")

    monkeypatch.setattr(web_module.asyncio, "to_thread", raise_missing_browser)
    monkeypatch.setattr(
        runtime,
        "coletar_conteudo_pagina_http",
        lambda url: asyncio.sleep(0, result="http-fallback"),
    )
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/thread-miss") == (
        "http-fallback"
    )

    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    monkeypatch.setattr(web_module.sys, "platform", "linux")

    async def raise_timeout(url):
        raise web_module.PlaywrightTimeoutError("timeout")

    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_timeout)
    monkeypatch.setattr(
        runtime,
        "coletar_conteudo_pagina_http",
        lambda url: asyncio.sleep(0, result=None),
    )
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/timeout") is None

    async def raise_missing_browser_core(url):
        raise RuntimeError("Executable doesn't exist")

    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_missing_browser_core)
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/missing-browser") is None


@pytest.mark.asyncio
async def test_llm_runtime_prefers_valid_system_key_when_user_key_is_invalid(monkeypatch):
    monkeypatch.setattr(
        web_module.settings,
        "OPENAI_API_KEY",
        "sk-system-12345678901234567890",
        raising=False,
    )

    captured = {}

    class _WorkflowStub:
        async def call_openai_api(self, **kwargs):
            captured.update(kwargs)
            return '{"nome_base":"Produto"}'

        def get_openai_provider_name(self):
            return "openai"

    runtime = web_module.WebLLMExtractionEngineRuntime(
        ai_provider_workflow_factory=lambda: _WorkflowStub()
    )

    result = await runtime.extrair_dados_produto_com_llm(
        texto_pagina="texto relevante sobre o produto",
        metadados_normalizados={"marca": "Marca"},
        campos_desejados=["nome_base"],
        produto_nome_base="Produto Base",
        user=SimpleNamespace(chave_openai_pessoal="adminpassword"),
    )

    assert result["nome_base"] == "Produto"
    assert captured["api_key"] == "sk-system-12345678901234567890"
