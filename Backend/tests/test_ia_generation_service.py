"""Module test ia generation service.

Contains backend logic related to test ia generation service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest

from Backend.application.services.ia_generation_service import IAGenerationService


class _PortStub:
    """Represent port stub and centralize responsibilities for this module."""
    def __init__(self) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    async def gerar_titulos_com_gemini(self, *, session, produto_id, user, num_titulos=3):
        """Run gerar titulos com gemini in this workflow."""
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

    async def gerar_titulos_com_openai(self, *, session, produto_id, user, num_titulos=3):
        """Run gerar titulos com openai in this workflow."""
        self.calls.append(
            (
                "gerar_titulos_com_openai",
                {
                    "session": session,
                    "produto_id": produto_id,
                    "user": user,
                    "num_titulos": num_titulos,
                },
            )
        )
        return ["o1", "o2"]

    async def gerar_descricao_com_openai(self, *, session, produto_id, user, tamanho_palavras=150):
        """Run gerar descricao com openai in this workflow."""
        self.calls.append(
            (
                "gerar_descricao_com_openai",
                {
                    "session": session,
                    "produto_id": produto_id,
                    "user": user,
                    "tamanho_palavras": tamanho_palavras,
                },
            )
        )
        return "descricao openai"

    async def gerar_descricao_com_gemini(self, *, session, produto_id, user, tamanho_palavras=150):
        """Run gerar descricao com gemini in this workflow."""
        self.calls.append(
            (
                "gerar_descricao_com_gemini",
                {
                    "session": session,
                    "produto_id": produto_id,
                    "user": user,
                    "tamanho_palavras": tamanho_palavras,
                },
            )
        )
        return "descricao gemini"

    async def sugerir_valores_atributos_com_gemini(self, *, session, produto_id, user):
        """Run sugerir valores atributos com gemini in this workflow."""
        self.calls.append(
            (
                "sugerir_valores_atributos_com_gemini",
                {"session": session, "produto_id": produto_id, "user": user},
            )
        )
        return {"atributos": []}


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_ia_generation_service_delegates_title_generation():
        """Run test ia generation service delegates title generation in this workflow."""
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
    async def test_ia_generation_service_delegates_openai_and_description_flows():
        """Cover the remaining OpenAI/Gemini description entrypoints."""
        port = _PortStub()
        service = IAGenerationService(port=port)

        assert await service.gerar_titulos_com_openai(
            session="db",
            produto_id=3,
            user="u",
            num_titulos=5,
        ) == ["o1", "o2"]
        assert await service.gerar_descricao_com_openai(
            session="db",
            produto_id=4,
            user="u",
            tamanho_palavras=200,
        ) == "descricao openai"
        assert await service.gerar_descricao_com_gemini(
            session="db",
            produto_id=5,
            user="u",
            tamanho_palavras=120,
        ) == "descricao gemini"

        assert [call[0] for call in port.calls] == [
            "gerar_titulos_com_openai",
            "gerar_descricao_com_openai",
            "gerar_descricao_com_gemini",
        ]

    @pytest.mark.asyncio
    async def test_ia_generation_service_delegates_attribute_suggestions():
        """Run test ia generation service delegates attribute suggestions in this workflow."""
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
test_ia_generation_service_delegates_openai_and_description_flows = (
    _TopLevelFunctionSurface.test_ia_generation_service_delegates_openai_and_description_flows
)
test_ia_generation_service_delegates_attribute_suggestions = _TopLevelFunctionSurface.test_ia_generation_service_delegates_attribute_suggestions


