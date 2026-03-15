"""Additional detailed coverage for web fetch/search runtime branches."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor as web_module


class _UrlOpenResponse:
    def __init__(self, body: str | bytes, content_type: str = "text/html"):
        self._body = body if isinstance(body, bytes) else body.encode("utf-8")
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

        async def close(self):
            calls["page_closed"] = True

    class FakeContext:
        async def new_page(self):
            calls["new_page"] = True
            return FakePage()

        async def close(self):
            calls["context_closed"] = True

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
        chromium = SimpleNamespace(
            launch=lambda **kwargs: (
                calls.update({"launch_kwargs": kwargs}) or asyncio.sleep(0, result=browser)
            )
        )

    class FakeAsyncPlaywright:
        async def __aenter__(self):
            return FakePlaywrightInstance()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(web_module, "async_playwright", lambda: FakeAsyncPlaywright())
    monkeypatch.setattr(web_module.settings, "PLAYWRIGHT_GOTO_TIMEOUT_MS", 31000, raising=False)
    monkeypatch.setattr(
        web_module.settings,
        "PLAYWRIGHT_PROXY_POOL_JSON",
        '[{"server":"http://proxy-a:8080","username":"user","password":"secret"}]',
        raising=False,
    )
    html = await runtime.coletar_conteudo_pagina_playwright_core("https://example.com/p")
    assert html == "<html>playwright</html>"
    assert calls["goto"] == ("https://example.com/p", 31000, "networkidle")
    assert calls["page_closed"] is True
    assert calls["context_closed"] is True
    assert calls["closed"] is True
    assert calls["launch_kwargs"]["proxy"]["server"] == "http://proxy-a:8080"
    assert calls["context_kwargs"]["ignore_https_errors"] is True


def test_content_fetch_engine_proxy_rotation_and_error_classification(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    monkeypatch.setattr(
        web_module.settings,
        "PLAYWRIGHT_PROXY_POOL_JSON",
        '["skip",{"server":"http://proxy-a:8080"},{"server":"http://proxy-b:8080","username":"u","password":"p"},{"invalid":true}]',
        raising=False,
    )

    first = runtime.get_next_playwright_proxy()
    second = runtime.get_next_playwright_proxy()
    third = runtime.get_next_playwright_proxy()

    assert first == {"server": "http://proxy-a:8080"}
    assert second == {"server": "http://proxy-b:8080", "username": "u", "password": "p"}
    assert third == {"server": "http://proxy-a:8080"}
    assert runtime.classify_playwright_error(RuntimeError("ERR_PROXY_CONNECTION_FAILED")) == "proxy"
    assert runtime.classify_playwright_error(web_module.PlaywrightTimeoutError("timeout")) == "timeout"
    assert runtime.classify_playwright_error(RuntimeError("Access denied by anti bot")) == "anti_bot"
    assert runtime.classify_playwright_error(RuntimeError("Executable doesn't exist")) == "browser_missing"


@pytest.mark.asyncio
async def test_content_fetch_engine_helper_branches_cover_invalid_config_and_safe_close(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )

    monkeypatch.setattr(web_module.settings, "PLAYWRIGHT_GOTO_TIMEOUT_MS", "oops", raising=False)
    assert runtime.get_playwright_goto_timeout_ms() == 30000

    monkeypatch.setattr(web_module.settings, "PLAYWRIGHT_PROXY_POOL_JSON", None, raising=False)
    assert runtime.get_playwright_proxy_pool() == []
    assert runtime.get_next_playwright_proxy() is None

    monkeypatch.setattr(web_module.settings, "PLAYWRIGHT_PROXY_POOL_JSON", "{broken", raising=False)
    assert runtime.get_playwright_proxy_pool() == []

    monkeypatch.setattr(web_module.settings, "PLAYWRIGHT_PROXY_POOL_JSON", '{"server":"http://proxy"}', raising=False)
    assert runtime.get_playwright_proxy_pool() == []

    await runtime._safe_close_playwright_resource(None)
    await runtime._safe_close_playwright_resource(object())

    class _BrokenCloser:
        async def close(self):
            raise RuntimeError("close failed")

    await runtime._safe_close_playwright_resource(_BrokenCloser())


@pytest.mark.asyncio
async def test_content_fetch_engine_playwright_core_without_proxy_keeps_launch_kwargs_minimal(monkeypatch):
    runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )
    calls = {}

    class FakePage:
        async def goto(self, url, timeout, wait_until):
            calls["goto"] = (url, timeout, wait_until)

        async def content(self):
            return "<html>no-proxy</html>"

    class FakeContext:
        async def new_page(self):
            return FakePage()

    class FakeBrowser:
        async def new_context(self, **kwargs):
            return FakeContext()

        async def close(self):
            return None

    class FakePlaywrightInstance:
        chromium = SimpleNamespace(
            launch=lambda **kwargs: (
                calls.update({"launch_kwargs": kwargs}) or asyncio.sleep(0, result=FakeBrowser())
            )
        )

    class FakeAsyncPlaywright:
        async def __aenter__(self):
            return FakePlaywrightInstance()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(web_module, "async_playwright", lambda: FakeAsyncPlaywright())
    monkeypatch.setattr(web_module.settings, "PLAYWRIGHT_PROXY_POOL_JSON", None, raising=False)
    html = await runtime.coletar_conteudo_pagina_playwright_core("https://example.com/no-proxy")
    assert html == "<html>no-proxy</html>"
    assert calls["launch_kwargs"] == {"headless": True}


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


def test_content_fetch_engine_extracts_visual_pdf_context_when_text_is_missing(monkeypatch):
    search_runtime = web_module.WebSearchEngineRuntime()
    fetch_runtime = web_module.WebContentFetchEngineRuntime(search_runtime=search_runtime)

    class _FakeRaster:
        def __init__(self, token):
            self._token = token

        def save(self, buffer, format):
            buffer.write(f"png-{self._token}".encode("ascii"))

    class _FakePageImage:
        def __init__(self, token):
            self.original = _FakeRaster(token)

    class _FakePdfPage:
        def __init__(self, token):
            self._token = token

        def extract_text(self, **kwargs):
            return ""

        def to_image(self, resolution):
            return _FakePageImage(self._token)

    class _FakePdfContext:
        def __enter__(self):
            return SimpleNamespace(pages=[_FakePdfPage("A"), _FakePdfPage("B")])

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        web_module,
        "urlopen",
        lambda req, timeout=20: _UrlOpenResponse(b"%PDF-1.4", "application/pdf"),
    )
    monkeypatch.setattr(web_module.pdfplumber, "open", lambda fp: _FakePdfContext())

    html = fetch_runtime.coletar_conteudo_pagina_http_sync("https://example.com/manual.pdf")

    assert 'data-tdai-page-image="1"' in html
    assert 'data-tdai-page-image="2"' in html
    assert "Documento PDF sem texto extraivel" in html


def test_content_fetch_engine_prioritizes_relevant_pdf_pages_for_visual_context(monkeypatch):
    search_runtime = web_module.WebSearchEngineRuntime()
    fetch_runtime = web_module.WebContentFetchEngineRuntime(search_runtime=search_runtime)

    monkeypatch.setenv("PDF_LLM_MAX_PAGE_IMAGES", "2")
    monkeypatch.setenv("PDF_LLM_PAGE_SCAN_LIMIT", "4")

    class _FakeRaster:
        def __init__(self, token):
            self._token = token

        def save(self, buffer, format):
            buffer.write(f"png-{self._token}".encode("ascii"))

    class _FakePageImage:
        def __init__(self, token):
            self.original = _FakeRaster(token)

    class _FakePdfPage:
        def __init__(self, token, text):
            self._token = token
            self._text = text

        def extract_text(self, **kwargs):
            return self._text

        def to_image(self, resolution):
            return _FakePageImage(self._token)

    class _FakePdfContext:
        def __enter__(self):
            return SimpleNamespace(
                pages=[
                    _FakePdfPage("cover", "Catalogo geral sumario institucional pagina 1"),
                    _FakePdfPage(
                        "pump",
                        "Produto Bomba de combustivel Bosch Referencia 0580454087B Aplicacao motores flex",
                    ),
                    _FakePdfPage(
                        "spec",
                        "Especificacoes tecnicas Codigo SKU 12972WV87B Voltagem 12V Conteudo da embalagem 1 unidade",
                    ),
                    _FakePdfPage("about", "Quem somos historia da empresa e politica de qualidade"),
                ]
            )

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        web_module,
        "urlopen",
        lambda req, timeout=20: _UrlOpenResponse(b"%PDF-1.4", "application/pdf"),
    )
    monkeypatch.setattr(web_module.pdfplumber, "open", lambda fp: _FakePdfContext())

    html = fetch_runtime.coletar_conteudo_pagina_http_sync("https://example.com/catalogo.pdf")

    assert 'data-tdai-page-image="2"' in html
    assert 'data-tdai-page-image="3"' in html
    assert 'data-tdai-page-image="1"' not in html
    assert 'data-tdai-page-image="4"' not in html
