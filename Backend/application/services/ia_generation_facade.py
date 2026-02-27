from __future__ import annotations

from typing import Any

from Backend.application.services.ports import IAGenerationPort
from Backend.infrastructure.legacy.ia_generation_bridge import LegacyIAGenerationBridge


class IAGenerationFacade:
    """Explicit OOP facade for IA generation service."""

    def __init__(
        self,
        legacy_module: Any = None,
        *,
        port: IAGenerationPort | None = None,
    ) -> None:
        self._port = port or legacy_module or LegacyIAGenerationBridge()

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_titulos_com_openai(*args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_descricao_com_openai(*args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_titulos_com_gemini(*args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_descricao_com_gemini(*args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._port.sugerir_valores_atributos_com_gemini(*args, **kwargs)
