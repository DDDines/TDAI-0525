from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.ia_generation_module import (
    get_ia_generation_workflow,
)


class IAGenerationRuntimeService:
    """Explicit runtime service surface for IA generation flows."""

    def __init__(self) -> None:
        self._workflow = get_ia_generation_workflow()

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._workflow.gerar_titulos_com_openai(*args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._workflow.gerar_descricao_com_openai(*args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._workflow.gerar_titulos_com_gemini(*args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._workflow.gerar_descricao_com_gemini(*args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._workflow.sugerir_valores_atributos_com_gemini(*args, **kwargs)


ia_generation_runtime_service = IAGenerationRuntimeService()

