"""Additional detailed coverage for web fetch/search runtime branches."""

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
async def test_content_fetch_engine_covers_selector_thread_and_notimplemented(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )

    class SelectorLoop:
        pass

    monkeypatch.setattr(web_module.sys, "platform", "win32")
    monkeypatch.setattr(web_module.asyncio, "get_running_loop", lambda: SelectorLoop())

    async def fake_to_thread(fn, *args):
        return fn(*args)

    monkeypatch.setattr(web_module.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(runtime, "coletar_conteudo_playwright_em_thread_sync", lambda url: f"thread:{url}")
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/thread") == "thread:https://example.com/thread"

    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    monkeypatch.setattr(web_module.sys, "platform", "linux")

    async def raise_not_implemented(url):
        raise NotImplementedError("loop unsupported")

    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_playwright_core", raise_not_implemented)
    monkeypatch.setattr(runtime, "coletar_conteudo_pagina_http", lambda url: asyncio.sleep(0, result="http-notimplemented"))
    assert await runtime.coletar_conteudo_pagina_playwright("https://example.com/ni") == "http-notimplemented"


@pytest.mark.asyncio
async def test_content_fetch_engine_playwright_core_closes_browser(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    calls = {}

    class FakePage:
        async def goto(self, url, timeout, wait_until):
            calls["goto"] = (url, timeout, wait_until)

        async def content(self):
            return "<html>playwright</html>"

    class FakeContext:
        async def new_page(self):
            calls["new_page"] = True
            return FakePage()

    class FakeBrowser:
        def __init__(self):
            self.closed = False

        async def new_context(self, **kwargs):
            calls["context_kwargs"] = kwargs
            return FakeContext()

        async def close(self):
            self.closed = True
            calls["closed"] = True

    browser = FakeBrowser()

    class FakePlaywrightInstance:
        chromium = SimpleNamespace(launch=lambda **kwargs: asyncio.sleep(0, result=browser))

    class FakeAsyncPlaywright:
        async def __aenter__(self):
            return FakePlaywrightInstance()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(web_module, "async_playwright", lambda: FakeAsyncPlaywright())
    html = await runtime.coletar_conteudo_pagina_playwright_core("https://example.com/p")
    assert html == "<html>playwright</html>"
    assert calls["goto"] == ("https://example.com/p", 30000, "networkidle")
    assert calls["closed"] is True


def test_search_engine_public_sync_proxy_fallback_and_non_html_http(monkeypatch):
    search_runtime = web_module.WebSearchEngineRuntime()
    fetch_runtime = web_module.WebContentFetchEngineRuntime(search_runtime=search_runtime)

    responses = [
        RuntimeError("duckdown"),
        RuntimeError("duckdown-2"),
        RuntimeError("bingdown"),
        _UrlOpenResponse("(https://example.com/produto-a)\n(https://example.com/produto-b)"),
    ]

    def fake_urlopen(req, timeout=8):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(web_module, "urlopen", fake_urlopen)
    urls = search_runtime.buscar_urls_publicas_sync("produto teste", num_results=2)
    assert urls == ["https://example.com/produto-a", "https://example.com/produto-b"]

    monkeypatch.setattr(web_module, "urlopen", lambda req, timeout=20: _UrlOpenResponse("bin", "application/pdf"))
    assert fetch_runtime.coletar_conteudo_pagina_http_sync("https://example.com/file") is None
