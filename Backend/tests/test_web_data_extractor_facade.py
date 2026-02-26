from __future__ import annotations

import pytest

from Backend.application.services.web_data_extractor_facade import (
    WebDataExtractorFacade,
)


class _LegacyWebStub:
    def __init__(self) -> None:
        self.calls = []

    def busca_publica_disponivel(self) -> bool:
        self.calls.append(("busca_publica_disponivel", (), {}))
        return True

    async def buscar_urls_google(self, *args, **kwargs):
        self.calls.append(("buscar_urls_google", args, kwargs))
        return ["https://example.org/a"]

    def _normalizar_dados_de_metadados(self, payload):
        self.calls.append(("_normalizar_dados_de_metadados", (payload,), {}))
        return {"nome": "ok"}


def test_web_data_extractor_facade_delegates_sync_call():
    legacy = _LegacyWebStub()
    facade = WebDataExtractorFacade(legacy_module=legacy)

    assert facade.busca_publica_disponivel() is True
    assert legacy.calls[0][0] == "busca_publica_disponivel"


@pytest.mark.asyncio
async def test_web_data_extractor_facade_delegates_async_call():
    legacy = _LegacyWebStub()
    facade = WebDataExtractorFacade(legacy_module=legacy)

    result = await facade.buscar_urls_google(query="abc", num_results=3)

    assert result == ["https://example.org/a"]
    assert legacy.calls[0][0] == "buscar_urls_google"
    assert legacy.calls[0][2] == {"query": "abc", "num_results": 3}


def test_web_data_extractor_facade_normalizes_metadata_via_adapter_method():
    legacy = _LegacyWebStub()
    facade = WebDataExtractorFacade(legacy_module=legacy)

    result = facade.normalizar_dados_de_metadados({"a": 1})

    assert result == {"nome": "ok"}
    assert legacy.calls[0][0] == "_normalizar_dados_de_metadados"

