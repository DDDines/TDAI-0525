"""Module test web data extractor engine runtime.

Contains backend logic related to test web data extractor engine runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_web_search_runtime_delega_para_engine_runtime():
        """Run test web search runtime delega para engine runtime in this workflow."""
        calls = []
    
        class FakeEngine:
            """Represent fake engine and centralize responsibilities for this module."""
            async def buscar_urls_publicas_async(self, *, query: str, num_results: int):
                """Run buscar urls publicas async in this workflow."""
                calls.append(("public", query, num_results))
                return ["https://example.com/public"]
    
            async def buscar_urls_google_async(self, *, query: str, num_results: int):
                """Run buscar urls google async in this workflow."""
                calls.append(("google", query, num_results))
                return ["https://example.com/google"]
    
        runtime = web_extractor.WebSearchRuntime(engine_runtime=FakeEngine())
    
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
        """Run test web content runtime delega para engine runtime in this workflow."""
        calls = []
    
        class FakeEngine:
            """Represent fake engine and centralize responsibilities for this module."""
            async def coletar_conteudo_pagina_playwright(self, url: str):
                """Run coletar conteudo pagina playwright in this workflow."""
                calls.append(url)
                return "<html>ok</html>"
    
        runtime = web_extractor.WebContentCollectionRuntime(engine_runtime=FakeEngine())
    
        html = await runtime.coletar_conteudo_pagina_playwright("https://example.com/p")
    
        assert html == "<html>ok</html>"
        assert calls == ["https://example.com/p"]

    def test_search_runtime_helpers_delegam_para_engine_runtime():
        """Run test search runtime helpers delegam para engine runtime in this workflow."""
        class FakeSearchEngine:
            """Represent fake search engine and centralize responsibilities for this module."""
            def get_search_cache_lock(self):
                """Return search cache lock for this workflow."""
                return object()
    
            def get_search_semaphore(self):
                """Return search semaphore for this workflow."""
                return object()
    
            async def search_cache_get(self, _query_key):
                """Run search cache get in this workflow."""
                return None
    
            async def search_cache_set(self, _query_key, _urls):
                """Run search cache set in this workflow."""
                return None
    
            def score_url_publica(self, _url: str):
                """Run score url publica in this workflow."""
                return 1
    
            def extract_redirect_destination(self, _query: str):
                """Extract redirect destination for this workflow."""
                return None
    
            def unwrap_redirect_url(self, url: str, max_hops: int = 3):
                """Run unwrap redirect url in this workflow."""
                _ = max_hops
                return url
    
            def busca_publica_disponivel(self):
                """Run busca publica disponivel in this workflow."""
                return False
    
            def url_deve_ser_ignorada_antes_da_coleta(self, url: str):
                """Run url deve ser ignorada antes da coleta in this workflow."""
                return url.endswith(".tmp")
    
            def normalizar_url_busca(self, candidata: str, base_url: str):
                """Run normalizar url busca in this workflow."""
                return f"{base_url}|{candidata}"
    
        runtime = web_extractor.WebSearchRuntime(engine_runtime=FakeSearchEngine())
        workflow = web_extractor.WebSearchWorkflow(runtime=runtime)
    
        assert workflow.busca_publica_disponivel() is False
        assert workflow.url_deve_ser_ignorada_antes_da_coleta("x.tmp") is True
        assert workflow.normalizar_url_busca("item", "https://base") == "https://base|item"

    @pytest.mark.asyncio
    async def test_web_llm_runtime_delega_para_engine_runtime():
        """Run test web llm runtime delega para engine runtime in this workflow."""
        called = {}
    
        class FakeEngine:
            """Represent fake engine and centralize responsibilities for this module."""
            async def extrair_dados_produto_com_llm(self, **kwargs):
                """Run extrair dados produto com llm in this workflow."""
                called.update(kwargs)
                return {"nome_base": "Produto X"}
    
        runtime = web_extractor.WebLLMExtractionRuntime(engine_runtime=FakeEngine())
        result = await runtime.extrair_dados_produto_com_llm(
            texto_pagina="texto",
            produto_nome_base="Produto X",
        )
    
        assert result == {"nome_base": "Produto X"}
        assert called["produto_nome_base"] == "Produto X"

    @pytest.mark.asyncio
    async def test_web_url_runtime_delega_para_engine_runtime():
        """Run test web url runtime delega para engine runtime in this workflow."""
        called = {}
    
        class FakeEngine:
            """Represent fake engine and centralize responsibilities for this module."""
            async def extract_relevant_data_from_url(self, **kwargs):
                """Extract relevant data from url for this workflow."""
                called.update(kwargs)
                return kwargs["produto"]
    
        runtime = web_extractor.WebURLExtractionRuntime(engine_runtime=FakeEngine())
        produto = object()
        returned = await runtime.extract_relevant_data_from_url(
            db="db",
            url="https://example.com/p",
            produto=produto,
        )
    
        assert returned is produto
        assert called["url"] == "https://example.com/p"

    def test_web_ocr_runtime_delega_para_engine_runtime():
        """Run test web ocr runtime delega para engine runtime in this workflow."""
        called = {}
    
        class FakeEngine:
            """Represent fake engine and centralize responsibilities for this module."""
            def extract_text_from_image_region(self, image_bytes: bytes):
                """Extract text from image region for this workflow."""
                called["image_bytes"] = image_bytes
                return {"text": "ok"}
    
        runtime = web_extractor.WebOCRRuntime(engine_runtime=FakeEngine())
        result = runtime.extract_text_from_image_region(b"img")
    
        assert result == {"text": "ok"}
        assert called["image_bytes"] == b"img"

test_web_search_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_search_runtime_delega_para_engine_runtime
test_web_content_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_content_runtime_delega_para_engine_runtime
test_search_runtime_helpers_delegam_para_engine_runtime = _TopLevelFunctionSurface.test_search_runtime_helpers_delegam_para_engine_runtime
test_web_llm_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_llm_runtime_delega_para_engine_runtime
test_web_url_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_url_runtime_delega_para_engine_runtime
test_web_ocr_runtime_delega_para_engine_runtime = _TopLevelFunctionSurface.test_web_ocr_runtime_delega_para_engine_runtime












