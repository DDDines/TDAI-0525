from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime.ia_generation_runtime import (
    get_runtime_service,
)


def _default_ia_generation_runtime_service() -> Any:
    return get_runtime_service()


class IAGenerationServiceAdapter:
    """OOP port adapter backed by the current IA generation implementation."""

    def __init__(self, service: Any | None = None) -> None:
        self._service = service or _default_ia_generation_runtime_service()

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._service.gerar_titulos_com_openai(*args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._service.gerar_descricao_com_openai(*args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._service.gerar_titulos_com_gemini(*args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._service.gerar_descricao_com_gemini(*args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._service.sugerir_valores_atributos_com_gemini(*args, **kwargs)
