from __future__ import annotations

import pytest

from Backend.application.services.web_data_extractor_components import (
    WebContentService,
    WebLLMService,
    WebOCRService,
    WebSearchService,
)


class _LegacyWebModuleStub:
    def __init__(self) -> None:
        self.calls = []

    def busca_publica_disponivel(self):
        self.calls.append(("busca_publica_disponivel", (), {}))
        return True

    async def buscar_urls_google(self, *args, **kwargs):
        self.calls.append(("buscar_urls_google", args, kwargs))
        return ["https://example.com"]

    async def coletar_conteudo_pagina_playwright(self, *args, **kwargs):
        self.calls.append(("coletar_conteudo_pagina_playwright", args, kwargs))
        return "<html></html>"

    async def extrair_dados_produto_com_llm(self, *args, **kwargs):
        self.calls.append(("extrair_dados_produto_com_llm", args, kwargs))
        return {"nome": "teste"}

    def extract_text_from_image_region(self, *args, **kwargs):
        self.calls.append(("extract_text_from_image_region", args, kwargs))
        return {"text": "ok"}


def test_web_search_service_delegates_sync_call():
    legacy = _LegacyWebModuleStub()
    service = WebSearchService(legacy)

    assert service.busca_publica_disponivel() is True
    assert legacy.calls[0][0] == "busca_publica_disponivel"


@pytest.mark.asyncio
async def test_web_search_service_delegates_async_call():
    legacy = _LegacyWebModuleStub()
    service = WebSearchService(legacy)

    result = await service.buscar_urls_google(query="abc", num_results=3)

    assert result == ["https://example.com"]
    assert legacy.calls[0][0] == "buscar_urls_google"


@pytest.mark.asyncio
async def test_web_content_service_delegates_fetch_call():
    legacy = _LegacyWebModuleStub()
    service = WebContentService(legacy)

    result = await service.coletar_conteudo_pagina_playwright("https://x")

    assert result == "<html></html>"
    assert legacy.calls[0][0] == "coletar_conteudo_pagina_playwright"


@pytest.mark.asyncio
async def test_web_llm_service_delegates_extraction_call():
    legacy = _LegacyWebModuleStub()
    service = WebLLMService(legacy)

    result = await service.extrair_dados_produto_com_llm(texto_pagina="x")

    assert result == {"nome": "teste"}
    assert legacy.calls[0][0] == "extrair_dados_produto_com_llm"


def test_web_ocr_service_delegates_ocr_call():
    legacy = _LegacyWebModuleStub()
    service = WebOCRService(legacy)

    result = service.extract_text_from_image_region(b"img")

    assert result == {"text": "ok"}
    assert legacy.calls[0][0] == "extract_text_from_image_region"

