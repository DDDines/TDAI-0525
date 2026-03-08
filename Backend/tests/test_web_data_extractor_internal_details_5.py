from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor as web_module


class _UrlOpenResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": "text/html"}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_search_runtime_covers_remaining_duckduckgo_and_proxy_paths(monkeypatch):
    runtime = web_module.WebSearchEngineRuntime()
    monkeypatch.setattr(runtime, "unwrap_redirect_url", lambda url, max_hops=4: url)

    assert runtime.normalizar_url_busca(
        "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fproduto",
        "https://duckduckgo.com/html/?q=produto",
    ) == "https://example.com/produto"

    assert runtime.normalizar_url_busca(
        "https://duckduckgo.com/l/?uddg=%20&u=https%3A%2F%2Fexample.com%2Fproduto-b",
        "https://duckduckgo.com/html/?q=produto",
    ) == "https://example.com/produto-b"

    assert (
        runtime.normalizar_url_busca(
            "https://duckduckgo.com/l/?u=https%3A%2F%2Fduckduckgo.com%2Fredirect",
            "https://duckduckgo.com/html/?q=produto",
        )
        is None
    )

    monkeypatch.setattr(
        runtime,
        "unwrap_redirect_url",
        lambda url, max_hops=4: "https://www.bing.com/aclick?x=1",
    )
    assert runtime.normalizar_url_busca("https://example.com/redir", "https://base") is None

    monkeypatch.setattr(
        runtime,
        "unwrap_redirect_url",
        lambda url, max_hops=4: "https://www.google.com/search?q=produto",
    )
    assert runtime.normalizar_url_busca("https://example.com/redir", "https://base") is None

    monkeypatch.setattr(runtime, "url_deve_ser_ignorada_antes_da_coleta", lambda url: True)
    monkeypatch.setattr(runtime, "unwrap_redirect_url", lambda url, max_hops=4: url)
    assert runtime.normalizar_url_busca("https://example.com/produto", "https://base") is None

    assert runtime.buscar_urls_publicas_sync("", num_results=1) == []

    html = """
    <html>
      <body>
        <a class="result__a" href="https://example.com/a">A</a>
        <a class="result__a" href="https://example.com/a">A2</a>
        <a class="result__a" href="">vazio</a>
      </body>
    </html>
    """
    responses = iter(
        [
            _UrlOpenResponse(html),
            _UrlOpenResponse("<html></html>"),
            _UrlOpenResponse("<html></html>"),
            _UrlOpenResponse("sem links aqui"),
        ]
    )
    monkeypatch.setattr(web_module, "urlopen", lambda req, timeout=8: next(responses))
    monkeypatch.setattr(runtime, "normalizar_url_busca", web_module.WebSearchEngineRuntime().normalizar_url_busca)
    assert runtime.buscar_urls_publicas_sync("produto", num_results=3) == ["https://example.com/a"]


@pytest.mark.asyncio
async def test_fetch_runtime_covers_remaining_thread_and_browser_flag_paths(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )

    class _SelectorLoop:
        pass

    monkeypatch.setattr(web_module.sys, "platform", "win32")
    monkeypatch.setattr(web_module.asyncio, "get_running_loop", lambda: _SelectorLoop())
    monkeypatch.setattr(
        web_module.asyncio,
        "to_thread",
        lambda func, *args: asyncio.sleep(0, result=None),
    )
    monkeypatch.setattr(
        runtime,
        "coletar_conteudo_pagina_http",
        lambda url: asyncio.sleep(0, result="http-from-empty-thread"),
    )
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/empty-thread") == (
        "http-from-empty-thread"
    )

    async def raise_generic_thread(func, *args):
        _ = func, args
        raise RuntimeError("generic thread failure")

    monkeypatch.setattr(web_module.asyncio, "to_thread", raise_generic_thread)
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/generic-thread") == (
        "http-from-empty-thread"
    )

    runtime.set_playwright_chromium_indisponivel(True)

    async def raise_missing_browser(url):
        raise RuntimeError("Executable doesn't exist")

    monkeypatch.setattr(web_module.sys, "platform", "linux")
    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_missing_browser)
    monkeypatch.setattr(
        runtime,
        "coletar_conteudo_pagina_http",
        lambda url: asyncio.sleep(0, result="http-after-browser-flag"),
    )
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/browser-flag") == (
        "http-after-browser-flag"
    )

    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )

    class _LoopNone:
        def run_until_complete(self, coro):
            coro.close()
            raise RuntimeError("loop creation failed")

        def close(self):
            return None

    monkeypatch.setattr(web_module.asyncio, "new_event_loop", lambda: (_ for _ in ()).throw(RuntimeError("no loop")))
    monkeypatch.setattr(web_module.asyncio, "set_event_loop", lambda loop: None)
    with pytest.raises(RuntimeError, match="no loop"):
        runtime.coletar_conteudo_playwright_em_thread_sync("https://example.com/no-loop")


def test_metadata_runtime_covers_opengraph_loop_followup(monkeypatch):
    runtime = web_module.MetadataExtractionRuntime()
    from collections import OrderedDict

    monkeypatch.setattr(
        web_module.extruct,
        "extract",
        lambda *args, **kwargs: OrderedDict(
            [
                ("opengraph", [{"og:title": "Produto OG"}]),
                ("json-ld", [{"@type": "Product", "name": "Produto JSON"}]),
            ]
        ),
    )

    extracted = runtime.extrair_metadados_estruturados("<html></html>", "https://example.com/p")
    assert extracted["opengraph"] == {"og:title": "Produto OG"}
    assert extracted["json-ld_product_candidate"]["name"] == "Produto JSON"


def test_metadata_runtime_skips_unknown_structured_syntax_and_keeps_iterating(monkeypatch):
    runtime = web_module.MetadataExtractionRuntime()
    from collections import OrderedDict

    monkeypatch.setattr(
        web_module.extruct,
        "extract",
        lambda *args, **kwargs: OrderedDict(
            [
                ("custom", [{"foo": "bar"}]),
                ("opengraph", [{"og:title": "Produto OG"}]),
            ]
        ),
    )

    extracted = runtime.extrair_metadados_estruturados("<html></html>", "https://example.com/p")
    assert extracted["opengraph"] == {"og:title": "Produto OG"}
