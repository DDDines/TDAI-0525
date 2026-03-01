from __future__ import annotations

import pytest

from Backend.application.services.ia_generation_service import IAGenerationService


class _PortStub:
    def __init__(self) -> None:
        self.calls = []

    async def gerar_titulos_com_gemini(self, *, session, produto_id, user, num_titulos=3):
        self.calls.append(
            (
                "gerar_titulos_com_gemini",
                {
                    "session": session,
                    "produto_id": produto_id,
                    "user": user,
                    "num_titulos": num_titulos,
                },
            )
        )
        return ["t1", "t2"]

    async def sugerir_valores_atributos_com_gemini(self, *, session, produto_id, user):
        self.calls.append(
            (
                "sugerir_valores_atributos_com_gemini",
                {"session": session, "produto_id": produto_id, "user": user},
            )
        )
        return {"atributos": []}


class _TopLevelFunctionSurface:

    @pytest.mark.asyncio
    async def test_ia_generation_service_delegates_title_generation():
        port = _PortStub()
        service = IAGenerationService(port=port)
    
        result = await service.gerar_titulos_com_gemini(
            session="db",
            produto_id=1,
            user="u",
        )
    
        assert result == ["t1", "t2"]
        assert port.calls[0][0] == "gerar_titulos_com_gemini"
        assert port.calls[0][1]["session"] == "db"
        assert port.calls[0][1]["produto_id"] == 1
        assert port.calls[0][1]["user"] == "u"

    @pytest.mark.asyncio
    async def test_ia_generation_service_delegates_attribute_suggestions():
        port = _PortStub()
        service = IAGenerationService(port=port)
    
        result = await service.sugerir_valores_atributos_com_gemini(
            session="db",
            produto_id=2,
            user="x",
        )
    
        assert result == {"atributos": []}
        assert port.calls[0][0] == "sugerir_valores_atributos_com_gemini"

test_ia_generation_service_delegates_title_generation = _TopLevelFunctionSurface.test_ia_generation_service_delegates_title_generation
test_ia_generation_service_delegates_attribute_suggestions = _TopLevelFunctionSurface.test_ia_generation_service_delegates_attribute_suggestions


