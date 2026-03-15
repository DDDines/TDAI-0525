"""Additional detailed coverage for web extractor runtime branches."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor as web_module


def test_search_engine_normalizar_url_busca_covers_remaining_tracking_branches():
    runtime = web_module.WebSearchEngineRuntime()

    assert (
        runtime.normalizar_url_busca(
            "https://duckduckgo.com/l/?q=produto",
            "https://duckduckgo.com/html/?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fduckduckgo.com%2Fhtml%2F%3Fq%3Dx",
            "https://duckduckgo.com/html/?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://www.bing.com/aclick?u=https%3A%2F%2Fexample.com%2Fp",
            "https://www.bing.com/search?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://www.bing.com/images/search?q=produto",
            "https://www.bing.com/search?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            "https://example.com/redirect",
            "https://www.google.com/search?q=produto",
        )
        is None
    )
    assert (
        runtime.normalizar_url_busca(
            f"https://example.com/produto?x={'a' * 600}",
            "https://www.google.com/search?q=produto",
        )
        is None
    )


def test_content_fetch_engine_thread_sync_covers_windows_policy_cleanup(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    fake_loop_calls = {"closed": False, "set": []}

    async def fake_core(url):
        _ = url
        return "<html>thread-win</html>"

    class FakeLoop:
        def run_until_complete(self, coro):
            name = getattr(getattr(coro, "cr_code", None), "co_name", "")
            coro.close()
            if name == "fake_core":
                return "<html>thread-win</html>"
            raise RuntimeError("shutdown asyncgens failed")

        def close(self):
            fake_loop_calls["closed"] = True

    class FakePolicy:
        def new_event_loop(self):
            return FakeLoop()

    monkeypatch.setattr(web_module.sys, "platform", "win32")
    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", fake_core)
    monkeypatch.setattr(
        web_module.asyncio,
        "WindowsProactorEventLoopPolicy",
        lambda: FakePolicy(),
        raising=False,
    )
    monkeypatch.setattr(
        web_module.asyncio,
        "set_event_loop",
        lambda loop: fake_loop_calls["set"].append(loop),
    )

    html = runtime.coletar_conteudo_playwright_em_thread_sync("https://example.com/p")
    assert html == "<html>thread-win</html>"
    assert fake_loop_calls["closed"] is True
    assert fake_loop_calls["set"][-1] is None


@pytest.mark.asyncio
async def test_content_fetch_engine_generic_playwright_error_uses_http_fallback(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    monkeypatch.setattr(web_module.sys, "platform", "linux")

    async def raise_generic(url):
        raise RuntimeError("generic playwright failure")

    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_generic)
    monkeypatch.setattr(
        runtime,
        "coletar_conteudo_pagina_http",
        lambda url: asyncio.sleep(0, result="http-fallback-generic"),
    )

    assert (
        await runtime.coletar_conteudo_pagina_playwright("https://example.com/produto")
        == "http-fallback-generic"
    )


def test_metadata_runtime_covers_trafilatura_and_microdata_opengraph_fallbacks(monkeypatch):
    runtime = web_module.MetadataExtractionRuntime()

    monkeypatch.setattr(
        web_module.trafilatura,
        "extract",
        lambda html_content, **kwargs: "texto principal limpo",
    )
    assert runtime.extrair_texto_principal_com_trafilatura(None) is None
    assert runtime.extrair_texto_principal_com_trafilatura("<html></html>") == "texto principal limpo"

    normalized = runtime.normalizar_dados_de_metadados(
        {
            "microdata_product_candidate": {
                "name": "Micro Nome",
                "description": "Micro Desc",
                "image": "https://img.micro",
                "brand": "Marca Micro",
                "sku": "SKU-MICRO",
            },
            "opengraph": {
                "og:title": "OG Nome",
                "og:description": "OG Desc",
                "og:image": "https://img.og",
                "og:type": "website",
                "og:site_name": "Marca Site",
            },
        }
    )
    assert normalized["nome"] == "Micro Nome"
    assert normalized["descricao_curta"] == "Micro Desc"
    assert normalized["imagem_url"] == "https://img.micro"
    assert normalized["marca"] == "Marca Micro"
    assert normalized["sku"] == "SKU-MICRO"

    normalized_og_product = runtime.normalizar_dados_de_metadados(
        {
            "opengraph": {
                "og:title": "Produto OG",
                "og:description": "Descricao OG",
                "og:image": "https://og.produto",
                "og:type": "product",
                "product:brand": "Marca OG",
            }
        }
    )
    assert normalized_og_product["nome"] == "Produto OG"
    assert normalized_og_product["marca"] == "Marca OG"


@pytest.mark.asyncio
async def test_web_llm_runtime_prioritizes_user_key_and_preserves_existing_metadata(monkeypatch):
    user_key = "sk-user-12345678901234567890"
    system_key = "sk-system-12345678901234567890"
    calls = {}

    class WorkflowStub:
        async def call_openai_api(self, **kwargs):
            calls.update(kwargs)
            return 'Resposta {"marca": null, "sku_original": "SKU-123"} fim'

        def get_openai_provider_name(self):
            return "openai"

    monkeypatch.setattr(web_module.settings, "OPENAI_API_KEY", system_key, raising=False)

    runtime = web_module.WebLLMExtractionEngineRuntime(
        ai_provider_workflow_factory=lambda: WorkflowStub()
    )
    result = await runtime.extrair_dados_produto_com_llm(
        texto_pagina="texto relevante",
        metadados_normalizados={"marca": "Marca Base", "nome": "Produto Base"},
        campos_desejados=["marca", "sku_original"],
        produto_nome_base="Produto Base",
        user=SimpleNamespace(chave_openai_pessoal=user_key),
    )

    assert calls["api_key"] == user_key
    assert calls["model"] == "gpt-3.5-turbo-0125"
    assert result["marca"] == "Marca Base"
    assert result["sku_original"] == "SKU-123"
    assert result["nome"] == "Produto Base"
