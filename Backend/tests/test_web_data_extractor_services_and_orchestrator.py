"""Coverage for web data extractor service wrappers and orchestrator."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.services.web_data_extractor.content_service import (
    WebDataExtractorContentService,
)
from Backend.application.services.web_data_extractor.llm_service import (
    WebDataExtractorLLMService,
)
from Backend.application.services.web_data_extractor.metadata_service import (
    WebDataExtractorMetadataService,
)
from Backend.application.services.web_data_extractor.ocr_service import (
    WebDataExtractorOCRService,
)
from Backend.application.services.web_data_extractor.orchestrator_service import (
    WebDataExtractorOrchestratorService,
)
from Backend.application.services.web_data_extractor.search_service import (
    WebDataExtractorSearchService,
)


class _PortStub:
    def __init__(self):
        self.calls = []

    def busca_publica_disponivel(self):
        self.calls.append(("busca_publica_disponivel",))
        return True

    async def buscar_urls_publicas(self, *, query: str, num_results: int):
        self.calls.append(("buscar_urls_publicas", query, num_results))
        return [f"public:{query}:{num_results}"]

    async def buscar_urls_google(self, *, query: str, num_results: int):
        self.calls.append(("buscar_urls_google", query, num_results))
        return [f"google:{query}:{num_results}"]

    async def coletar_conteudo_pagina_playwright(self, *, url: str):
        self.calls.append(("coletar_conteudo_pagina_playwright", url))
        return f"<html>{url}</html>"

    def extrair_texto_principal_com_trafilatura(self, *, html_content: str):
        self.calls.append(("extrair_texto_principal_com_trafilatura", html_content))
        return "texto principal"

    def extrair_metadados_estruturados(self, *, html_content: str, url: str):
        self.calls.append(("extrair_metadados_estruturados", html_content, url))
        return {"url": url, "html": html_content}

    def normalizar_dados_de_metadados(self, *, metadata_bruta):
        self.calls.append(("normalizar_dados_de_metadados", metadata_bruta))
        return {"normalizado": metadata_bruta}

    async def extrair_dados_produto_com_llm(
        self,
        *,
        texto_pagina,
        metadados_normalizados,
        campos_desejados,
        produto_nome_base,
        user,
    ):
        self.calls.append(
            (
                "extrair_dados_produto_com_llm",
                texto_pagina,
                metadados_normalizados,
                tuple(campos_desejados or []),
                produto_nome_base,
                user,
            )
        )
        return {"nome": produto_nome_base}

    async def extract_relevant_data_from_url(self, *, session, url: str, produto):
        self.calls.append(("extract_relevant_data_from_url", session, url, produto))
        return produto

    def extract_text_from_image_region(self, image_bytes: bytes):
        self.calls.append(("extract_text_from_image_region", image_bytes))
        return "ocr-text"


@pytest.mark.asyncio
async def test_web_data_extractor_wrapper_services_delegate_to_port():
    port = _PortStub()

    search = WebDataExtractorSearchService(port)
    content = WebDataExtractorContentService(port)
    metadata = WebDataExtractorMetadataService(port)
    llm = WebDataExtractorLLMService(port)
    ocr = WebDataExtractorOCRService(port)

    assert search.busca_publica_disponivel() is True
    assert await search.buscar_urls_publicas(query="produto", num_results=4) == ["public:produto:4"]
    assert await search.buscar_urls_google(query="produto", num_results=2) == ["google:produto:2"]
    assert await content.coletar_conteudo_pagina_playwright(url="https://example.com") == "<html>https://example.com</html>"
    assert content.extrair_texto_principal_com_trafilatura(html_content="<html/>") == "texto principal"
    assert metadata.extrair_metadados_estruturados(html_content="<html/>", url="https://example.com") == {
        "url": "https://example.com",
        "html": "<html/>",
    }
    assert metadata.normalizar_dados_de_metadados(metadata_bruta={"x": 1}) == {"normalizado": {"x": 1}}
    assert await llm.extrair_dados_produto_com_llm(
        texto_pagina="conteudo",
        metadados_normalizados={"marca": "A"},
        campos_desejados=["marca"],
        produto_nome_base="Produto",
        user="user-1",
    ) == {"nome": "Produto"}
    produto = SimpleNamespace(id=5)
    assert await llm.extract_relevant_data_from_url(session="db", url="https://example.com", produto=produto) is produto
    assert ocr.extract_text_from_image_region(b"img") == "ocr-text"


@pytest.mark.asyncio
async def test_web_data_extractor_orchestrator_exposes_all_service_paths():
    port = _PortStub()
    service = WebDataExtractorOrchestratorService(port)

    assert service.busca_publica_disponivel() is True
    assert await service.buscar_urls_publicas("produto", 3) == ["public:produto:3"]
    assert await service.buscar_urls_google("produto", 1) == ["google:produto:1"]
    assert await service.coletar_conteudo_pagina_playwright("https://example.com") == "<html>https://example.com</html>"
    assert service.extrair_texto_principal_com_trafilatura("<html/>") == "texto principal"
    assert service.extrair_metadados_estruturados("<html/>", "https://example.com") == {
        "url": "https://example.com",
        "html": "<html/>",
    }
    assert service.normalizar_dados_de_metadados({"x": 1}) == {"normalizado": {"x": 1}}
    produto = SimpleNamespace(id=10)
    assert await service.extrair_dados_produto_com_llm(
        "texto",
        {"meta": True},
        ["nome"],
        "Produto Base",
        "user-1",
    ) == {"nome": "Produto Base"}
    assert await service.extract_relevant_data_from_url(session="db", url="https://example.com", produto=produto) is produto
    assert service.extract_text_from_image_region(b"img") == "ocr-text"
