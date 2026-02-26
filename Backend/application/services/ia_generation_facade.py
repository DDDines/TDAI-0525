from __future__ import annotations

from typing import Any

from Backend.services import ia_generation_service as legacy_ia_generation_service


class IAGenerationFacade:
    """Adaptador OO para o módulo legado de geração de conteúdo IA."""

    def __init__(self, legacy_module: Any = legacy_ia_generation_service) -> None:
        self._legacy = legacy_module

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._legacy.gerar_titulos_com_openai(*args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._legacy.gerar_descricao_com_openai(*args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._legacy.gerar_titulos_com_gemini(*args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._legacy.gerar_descricao_com_gemini(*args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._legacy.sugerir_valores_atributos_com_gemini(
            *args, **kwargs
        )

    def __getattr__(self, item: str) -> Any:
        return getattr(self._legacy, item)

