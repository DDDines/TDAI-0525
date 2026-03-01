from __future__ import annotations

from typing import Any

from Backend.application.services.ports import IAGenerationPort
from Backend.infrastructure.adapters.ia_generation_adapter import (
    IAGenerationServiceAdapter,
)


class IAGenerationService:
    """Explicit OOP service for IA generation flows."""

    def __init__(
        self,
        *,
        port: IAGenerationPort | None = None,
    ) -> None:
        self._port = port or IAGenerationServiceAdapter()

    @staticmethod
    def _normalize_runtime_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(kwargs)
        if "session" in normalized and "db" not in normalized:
            normalized["db"] = normalized.pop("session")
        return normalized

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_titulos_com_openai(
            *args, **self._normalize_runtime_kwargs(kwargs)
        )

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_descricao_com_openai(
            *args, **self._normalize_runtime_kwargs(kwargs)
        )

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_titulos_com_gemini(
            *args, **self._normalize_runtime_kwargs(kwargs)
        )

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_descricao_com_gemini(
            *args, **self._normalize_runtime_kwargs(kwargs)
        )

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._port.sugerir_valores_atributos_com_gemini(
            *args, **self._normalize_runtime_kwargs(kwargs)
        )
