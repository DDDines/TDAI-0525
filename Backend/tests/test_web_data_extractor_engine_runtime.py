from __future__ import annotations

import pytest

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

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
            async def coletar_conteudo_pagina_playwright(self, url: str):
                calls.append(url)
                return "<html>ok</html>"
    
        runtime = web_extractor._WebContentCollectionRuntime(engine_runtime=FakeEngine())
    
        html = await runtime.coletar_conteudo_pagina_playwright("https://example.com/p")
    
        assert html == "<html>ok</html>"
        assert calls == ["https://example.com/p"]

    def test_search_runtime_helpers_delegam_para_engine_runtime():
        class FakeSearchEngine:
            def get_search_cache_lock(self):
                return object()
    
            def get_search_semaphore(self):
                return object()
    
            async def search_cache_get(self, _query_key):
                return None
    
            async def search_cache_set(self, _query_key, _urls):
                return None
    
            def score_url_publica(self, _url: str):
                return 1
    
            def extract_redirect_destination(self, _query: str):
                return None
    
            def unwrap_redirect_url(self, url: str, max_hops: int = 3):
                _ = max_hops
                return url
    
            def busca_publica_disponivel(self):
                return False
    
            def url_deve_ser_ignorada_antes_da_coleta(self, url: str):
                return url.endswith(".tmp")
    
            def normalizar_url_busca(self, candidata: str, base_url: str):
                return f"{base_url}|{candidata}"
    
        runtime = web_extractor._WebSearchRuntime(engine_runtime=FakeSearchEngine())
        workflow = web_extractor._WebSearchWorkflow(runtime=runtime)
    
        assert workflow.busca_publica_disponivel() is False
        assert workflow.url_deve_ser_ignorada_antes_da_coleta("x.tmp") is True
        assert workflow.normalizar_url_busca("item", "https://base") == "https://base|item"

    @pytest.mark.asyncio
    async def test_web_llm_runtime_delega_para_engine_runtime():
        called = {}
    
        class FakeEngine:
            async def extrair_dados_produto_com_llm(self, **kwargs):
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
            async def extract_relevant_data_from_url(self, **kwargs):
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
            def extract_text_from_image_region(self, image_bytes: bytes):
                called["image_bytes"] = image_bytes
                return {"text": "ok"}
    
        runtime = web_extractor._WebOCRRuntime(engine_runtime=FakeEngine())
        result = runtime.extract_text_from_image_region(b"img")
    
        assert result == {"text": "ok"}
        assert called["image_bytes"] == b"img"

test_web_search_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_search_runtime_delega_para_engine_runtime
test_web_content_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_content_runtime_delega_para_engine_runtime
test_search_runtime_helpers_delegam_para_engine_runtime = _TopLevelFunctionSurface.test_search_runtime_helpers_delegam_para_engine_runtime
test_web_llm_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_llm_runtime_delega_para_engine_runtime
test_web_url_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_url_runtime_delega_para_engine_runtime
test_web_ocr_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_ocr_runtime_delega_para_engine_runtime











