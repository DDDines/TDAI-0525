"""Module test web data extractor workflows runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_web_search_workflow_usa_runtime_injetado():
        """Execute test_web_search_workflow_usa_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        called = []
    
        class FakeSearchRuntime:
            """Class FakeSearchRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def buscar_urls_publicas_async(self, *, query: str, num_results: int = 3):
                """Execute buscar_urls_publicas_async.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("public", query, num_results))
                return ["https://example.com/publico"]
    
            async def buscar_urls_google_async(self, *, query: str, num_results: int = 3):
                """Execute buscar_urls_google_async.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("google", query, num_results))
                return ["https://example.com/google"]
    
        workflow = web_extractor.WebSearchWorkflow(runtime=FakeSearchRuntime())
    
        public_urls = await workflow.buscar_urls_publicas("peca automotiva", 2)
        google_urls = await workflow.buscar_urls_google("peca automotiva", 1)
    
        assert public_urls == ["https://example.com/publico"]
        assert google_urls == ["https://example.com/google"]
        assert called == [
            ("public", "peca automotiva", 2),
            ("google", "peca automotiva", 1),
        ]

    @pytest.mark.asyncio
    async def test_web_content_workflow_usa_runtime_injetado():
        """Execute test_web_content_workflow_usa_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        class FakeContentRuntime:
            """Class FakeContentRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def coletar_conteudo_pagina_playwright(self, url: str):
                """Execute coletar_conteudo_pagina_playwright.

                This callable is documented to make behavior explicit for readers.
                """
                called["url"] = url
                return "<html><body>ok</body></html>"
    
        workflow = web_extractor.WebContentCollectionWorkflow(
            runtime=FakeContentRuntime()
        )
        html = await workflow.coletar_conteudo_pagina_playwright("https://example.com/p")
    
        assert html == "<html><body>ok</body></html>"
        assert called["url"] == "https://example.com/p"

    @pytest.mark.asyncio
    async def test_web_extraction_support_workflow_usa_runtimes_injetados():
        """Execute test_web_extraction_support_workflow_usa_runtimes_injetados.

        This callable is documented to make behavior explicit for readers.
        """
        calls = {}
    
        class FakeMetadataRuntime:
            """Class FakeMetadataRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def extrair_texto_principal_com_trafilatura(self, html_content: str):
                """Execute extrair_texto_principal_com_trafilatura.

                This callable is documented to make behavior explicit for readers.
                """
                calls["texto"] = html_content
                return "texto extraido"
    
            def extrair_metadados_estruturados(self, html_content: str, url: str):
                """Execute extrair_metadados_estruturados.

                This callable is documented to make behavior explicit for readers.
                """
                calls["metadata"] = (html_content, url)
                return {"json-ld_product_candidate": {"name": "Produto X"}}
    
            def normalizar_dados_de_metadados(self, metadata_bruta):
                """Execute normalizar_dados_de_metadados.

                This callable is documented to make behavior explicit for readers.
                """
                calls["metadata_normalized"] = metadata_bruta
                return {"nome": "Produto X"}
    
        class FakeLLMRuntime:
            """Class FakeLLMRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def extrair_dados_produto_com_llm(self, **kwargs):
                """Execute extrair_dados_produto_com_llm.

                This callable is documented to make behavior explicit for readers.
                """
                calls["llm"] = kwargs
                return {"nome_base": "Produto X"}
    
        class FakeURLRuntime:
            """Class FakeURLRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def extract_relevant_data_from_url(self, **kwargs):
                """Execute extract_relevant_data_from_url.

                This callable is documented to make behavior explicit for readers.
                """
                calls["url_runtime"] = kwargs
                return kwargs["produto"]
    
        class FakeOCRRuntime:
            """Class FakeOCRRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def extract_text_from_image_region(self, image_bytes: bytes):
                """Execute extract_text_from_image_region.

                This callable is documented to make behavior explicit for readers.
                """
                calls["ocr"] = image_bytes
                return {"text": "anotacao"}
    
        workflow = web_extractor.WebExtractionSupportWorkflow(
            metadata_runtime=FakeMetadataRuntime(),
            llm_runtime=FakeLLMRuntime(),
            enrichment_runtime=FakeURLRuntime(),
            ocr_runtime=FakeOCRRuntime(),
        )
    
        assert (
            workflow.extrair_texto_principal_com_trafilatura("<html>ok</html>")
            == "texto extraido"
        )
        assert workflow.extrair_metadados_estruturados(
            "<html>ok</html>", "https://example.com"
        ) == {"json-ld_product_candidate": {"name": "Produto X"}}
        assert workflow.normalizar_dados_de_metadados(
            {"json-ld_product_candidate": {"name": "Produto X"}}
        ) == {"nome": "Produto X"}
    
        llm_result = await workflow.extrair_dados_produto_com_llm(
            texto_pagina="texto",
            produto_nome_base="Produto X",
        )
        assert llm_result == {"nome_base": "Produto X"}
    
        produto = SimpleNamespace(id=1, nome_base="Produto X")
        extracted_produto = await workflow.extract_relevant_data_from_url(
            db=object(),
            url="https://example.com/item",
            produto=produto,
        )
        assert extracted_produto is produto
    
        ocr = workflow.extract_text_from_image_region(b"img")
        assert ocr == {"text": "anotacao"}
    
        assert calls["texto"] == "<html>ok</html>"
        assert calls["metadata"][1] == "https://example.com"
        assert calls["metadata_normalized"] == {"json-ld_product_candidate": {"name": "Produto X"}}
        assert calls["llm"]["produto_nome_base"] == "Produto X"
        assert calls["url_runtime"]["url"] == "https://example.com/item"
        assert calls["ocr"] == b"img"

test_web_search_workflow_usa_runtime_injetado = _TopLevelFunctionSurface.test_web_search_workflow_usa_runtime_injetado
test_web_content_workflow_usa_runtime_injetado = _TopLevelFunctionSurface.test_web_content_workflow_usa_runtime_injetado
test_web_extraction_support_workflow_usa_runtimes_injetados = _TopLevelFunctionSurface.test_web_extraction_support_workflow_usa_runtimes_injetados






