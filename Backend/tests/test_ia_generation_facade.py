from __future__ import annotations

import pytest

from Backend.application.services.ia_generation_facade import IAGenerationFacade


class _LegacyIAStub:
    def __init__(self) -> None:
        self.calls = []

    async def gerar_titulos_com_gemini(self, *args, **kwargs):
        self.calls.append(("gerar_titulos_com_gemini", args, kwargs))
        return ["t1", "t2"]

    async def sugerir_valores_atributos_com_gemini(self, *args, **kwargs):
        self.calls.append(("sugerir_valores_atributos_com_gemini", args, kwargs))
        return {"atributos": []}


@pytest.mark.asyncio
async def test_ia_generation_facade_delegates_title_generation():
    legacy = _LegacyIAStub()
    facade = IAGenerationFacade(port=legacy)

    result = await facade.gerar_titulos_com_gemini(produto_id=1, user="u")

    assert result == ["t1", "t2"]
    assert legacy.calls[0][0] == "gerar_titulos_com_gemini"
    assert legacy.calls[0][2] == {"produto_id": 1, "user": "u"}


@pytest.mark.asyncio
async def test_ia_generation_facade_delegates_attribute_suggestions():
    legacy = _LegacyIAStub()
    facade = IAGenerationFacade(port=legacy)

    result = await facade.sugerir_valores_atributos_com_gemini(produto_id=2, user="x")

    assert result == {"atributos": []}
    assert legacy.calls[0][0] == "sugerir_valores_atributos_com_gemini"
