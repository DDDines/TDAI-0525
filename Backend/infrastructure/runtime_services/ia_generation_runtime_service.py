from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules import ia_generation_module


class IAGenerationRuntimeService:
    """Explicit runtime service surface for IA generation flows."""

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await ia_generation_module.gerar_titulos_com_openai(*args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await ia_generation_module.gerar_descricao_com_openai(*args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await ia_generation_module.gerar_titulos_com_gemini(*args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await ia_generation_module.gerar_descricao_com_gemini(*args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await ia_generation_module.sugerir_valores_atributos_com_gemini(
            *args,
            **kwargs,
        )


ia_generation_runtime_service = IAGenerationRuntimeService()

