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
async def test_search_runtime_covers_cache_eviction_helper_branches_and_google_cse(monkeypatch):
    runtime = web_module.WebSearchEngineRuntime()

    assert runtime.busca_publica_disponivel() is True
    runtime._search_cache = {"oldest": (1.0, ["https://old"])}
    runtime._search_cache_max_entries = 1
    await runtime.search_cache_set("new", ["https://new"])
    assert "oldest" not in runtime._search_cache
    assert await runtime.search_cache_get("new") == ["https://new"]

    assert runtime.score_url_publica(f"https://example.com/p/manual.pdf?x={'a' * 400}") < 0
    assert runtime.extract_redirect_destination("u=%2Frelative&url=https%3A%2F%2Fexample.com%2Fp") == (
        "https://example.com/p"
    )

    runtime_unwrap = web_module.WebSearchEngineRuntime()
    runtime_unwrap.extract_redirect_destination = lambda query: "https://example.com/p"
    assert runtime_unwrap.unwrap_redirect_url("https://example.com/p", max_hops=2) == "https://example.com/p"

    assert runtime.url_deve_ser_ignorada_antes_da_coleta("https:///sem-host") is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta("https://www.bing.com/ck/?u=x") is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta("https://www.bing.com/images/search?q=produto") is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta("https://www.google.com/url?q=x") is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta("https://example.com/p?utm_source=teste") is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta(f"https://example.com/p?x={'a' * 600}") is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta(
        "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fp"
    ) is True
    assert runtime.url_deve_ser_ignorada_antes_da_coleta("https://example.com/catalogo/manual.pdf") is False

    assert runtime.normalizar_url_busca("", "https://base") is None
    assert runtime.normalizar_url_busca("   ", "https://base") is None
    assert runtime.normalizar_url_busca(
        "https://duckduckgo.com/l/?q=produto",
        "https://duckduckgo.com/html/?q=produto",
    ) is None
    assert runtime.normalizar_url_busca(
        "mailto:teste@example.com",
        "https://base",
    ) is None
    assert runtime.normalizar_url_busca(
        "https://example.com/path",
        "https://base",
    ) == "https://example.com/path"

    async def fake_public(query, num_results=3):
        return ["https://publica.com/a"]

    monkeypatch.setattr(web_module, "GOOGLE_API_CLIENT_INSTALLED", True)
    monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_API_KEY", "key", raising=False)
    monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_ID", "cx", raising=False)

    class _Service:
        def cse(self):
            return self

        def list(self, **kwargs):
            return self

        def execute(self):
            return {"items": [{"link": "https://example.com/google"}]}

    monkeypatch.setattr(web_module, "build", lambda *args, **kwargs: _Service())
    assert runtime._executar_busca_google_cse("produto", 1) == ["https://example.com/google"]

    monkeypatch.setattr(runtime, "buscar_urls_publicas_async", fake_public)
    assert await runtime.buscar_urls_google_async("", num_results=1) == []


@pytest.mark.asyncio
async def test_search_runtime_covers_cached_google_empty_google_error_and_public_empty(monkeypatch):
    runtime = web_module.WebSearchEngineRuntime()
    await runtime.search_cache_set("produto::fallback", ["https://cached/a", "https://cached/b"])
    assert await runtime.buscar_urls_google_async("produto", num_results=1) == ["https://cached/a"]

    monkeypatch.setattr(web_module, "GOOGLE_API_CLIENT_INSTALLED", True)
    monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_API_KEY", "key", raising=False)
    monkeypatch.setattr(web_module.settings, "GOOGLE_CSE_ID", "cx", raising=False)
    monkeypatch.setattr(runtime, "_executar_busca_google_cse", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        runtime,
        "buscar_urls_publicas_async",
        lambda query, num_results=3: asyncio.sleep(0, result=[]),
    )
    assert await runtime.buscar_urls_google_async("produto-novo", num_results=2) == []

    def raising_google(*args, **kwargs):
        raise RuntimeError("google down")

    monkeypatch.setattr(runtime, "_executar_busca_google_cse", raising_google)
    monkeypatch.setattr(
        runtime,
        "buscar_urls_publicas_async",
        lambda query, num_results=3: asyncio.sleep(0, result=["https://publica/item"]),
    )
    assert await runtime.buscar_urls_google_async("produto-outro", num_results=1) == [
        "https://publica/item"
    ]


def test_public_search_and_metadata_branches_cover_proxy_and_non_product_cases(monkeypatch):
    runtime = web_module.WebSearchEngineRuntime()

    responses = iter(
        [
            _UrlOpenResponse("<html>sem anchors</html>"),
            _UrlOpenResponse("<html>sem anchors</html>"),
            _UrlOpenResponse("<html>sem anchors</html>"),
            _UrlOpenResponse(
                "(https://example.com/item-a)\n(https://example.com/item-a)\n(https://example.com/item-b)"
            ),
        ]
    )
    monkeypatch.setattr(web_module, "urlopen", lambda req, timeout=8: next(responses))
    assert runtime.buscar_urls_publicas_sync("produto", num_results=2) == [
        "https://example.com/item-a",
        "https://example.com/item-b",
    ]

    responses = iter(
        [
            _UrlOpenResponse("<html>sem anchors</html>"),
            _UrlOpenResponse("<html>sem anchors</html>"),
            _UrlOpenResponse("<html>sem anchors</html>"),
        ]
    )

    def fake_urlopen(req, timeout=8):
        try:
            return next(responses)
        except StopIteration:
            raise RuntimeError("proxy down")

    monkeypatch.setattr(web_module, "urlopen", fake_urlopen)
    assert runtime.buscar_urls_publicas_sync("produto", num_results=1) == []

    metadata_runtime = web_module.MetadataExtractionRuntime()
    assert metadata_runtime.limpar_valor_metadado(7) == 7
    assert metadata_runtime._get_first_string([None, ""]) is None
    assert metadata_runtime.extrair_metadados_estruturados("", "https://example.com") == {}

    monkeypatch.setattr(
        web_module.extruct,
        "extract",
        lambda *args, **kwargs: {
            "json-ld": [{"@type": "Thing", "name": "Ignorar"}],
            "microdata": [],
            "opengraph": [],
        },
    )
    fallback_metadata = metadata_runtime.extrair_metadados_estruturados(
        "<html></html>",
        "https://example.com",
    )
    assert fallback_metadata["dom_product_candidate"]["texto_estruturado_produto"].startswith(
        "URL da fonte: https://example.com"
    )

    normalized = metadata_runtime.normalizar_dados_de_metadados(
        {
            "json-ld_product_candidate": {
                "name": "Produto",
                "brand": "Marca",
                "offers": [],
            }
        }
    )
    assert normalized["nome"] == "Produto"
    assert normalized["marca"] == "Marca"
    assert "preco" not in normalized

    normalized_availability = metadata_runtime.normalizar_dados_de_metadados(
        {
            "json-ld_product_candidate": {
                "name": "Produto",
                "offers": {"availability": "Sem estoque"},
            }
        }
    )
    assert normalized_availability["disponibilidade"] == "Sem estoque"


@pytest.mark.asyncio
async def test_llm_and_enrichment_workflow_cover_context_insufficient_and_warning_logs():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        web_module.settings,
        "OPENAI_API_KEY",
        "sk-system-12345678901234567890",
        raising=False,
    )

    runtime = web_module.WebLLMExtractionEngineRuntime(
        ai_provider_workflow_factory=lambda: SimpleNamespace()
    )
    result = await runtime.extrair_dados_produto_com_llm(
        texto_pagina=None,
        metadados_normalizados={"nome": ""},
        campos_desejados=["nome"],
        produto_nome_base="Produto",
    )
    assert result == {"erro_llm": "Contexto insuficiente para processar"}

    class _Db:
        def __init__(self):
            self.added = []
            self.commits = 0
            self.refreshes = []

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            self.commits += 1

        def refresh(self, obj, attribute_names=None):
            self.refreshes.append((obj, attribute_names))

    produto = SimpleNamespace(
        id=9,
        dados_brutos_web=None,
        log_enriquecimento_web=None,
        status_enriquecimento_web=None,
    )
    db = _Db()
    workflow = web_module.WebExtractionEnrichmentWorkflow(
        db=db,
        url="https://example.com/p",
        produto=produto,
        runtime=SimpleNamespace(
            now_iso=lambda: "2026-03-08T00:00:00+00:00",
            collect_html=lambda url: asyncio.sleep(0, result="<html></html>"),
            extract_main_text=lambda html_content: "",
            extract_structured_metadata=lambda html_content, url: {},
            normalize_metadata=lambda metadata: {},
        ),
    )

    produto_final = await workflow.run()

    assert produto_final.status_enriquecimento_web == web_module.models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
    messages = [entry["message"] for entry in workflow.log_enriquecimento]
    assert "Nao foi possivel extrair texto principal com Trafilatura." in messages
    assert "Nenhum metadado estruturado (JSON-LD, Microdata, Opengraph) encontrado." in messages
    monkeypatch.undo()


@pytest.mark.asyncio
async def test_llm_runtime_covers_non_dict_payload_and_selector_timeout_fallback(monkeypatch):
    monkeypatch.setattr(
        web_module.settings,
        "OPENAI_API_KEY",
        "sk-system-12345678901234567890",
        raising=False,
    )

    class _WorkflowStub:
        async def call_openai_api(self, **kwargs):
            return '["payload-nao-dict"]'

        def get_openai_provider_name(self):
            return "openai"

    runtime = web_module.WebLLMExtractionEngineRuntime(
        ai_provider_workflow_factory=lambda: _WorkflowStub()
    )
    result = await runtime.extrair_dados_produto_com_llm(
        texto_pagina="texto relevante",
        metadados_normalizados={"marca": "Base"},
        campos_desejados=["marca"],
        produto_nome_base="Produto",
    )
    assert result == {"marca": "Base"}

    fetch_runtime = web_module.WebContentFetchEngineRuntime(
        search_runtime=SimpleNamespace(url_deve_ser_ignorada_antes_da_coleta=lambda url: False)
    )

    class _SelectorLoop:
        pass

    monkeypatch.setattr(web_module.sys, "platform", "win32")
    monkeypatch.setattr(web_module.asyncio, "get_running_loop", lambda: _SelectorLoop())
    monkeypatch.setattr(
        web_module.asyncio,
        "to_thread",
        lambda func, *args: (_ for _ in ()).throw(web_module.PlaywrightTimeoutError("timeout")),
    )
    monkeypatch.setattr(
        fetch_runtime,
        "coletar_conteudo_pagina_http",
        lambda url: asyncio.sleep(0, result="http-timeout"),
    )
    assert await fetch_runtime.coletar_conteudo_pagina_playwright("https://example.com/p") == "http-timeout"
