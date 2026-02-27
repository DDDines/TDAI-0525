from __future__ import annotations

from typing import Any, Optional

from Backend.core.legacy_guard import assert_legacy_usage_allowed
from Backend.services import ia_generation_service


class LegacyIAGenerationBridge:
    """Bridge explicito para o modulo legado de geracao IA."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or ia_generation_service

    @staticmethod
    def _assert_legacy_allowed() -> None:
        assert_legacy_usage_allowed(
            "Backend.infrastructure.legacy.LegacyIAGenerationBridge"
        )

    async def _call_async(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return await getattr(self._module, method_name)(*args, **kwargs)

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._call_async("gerar_titulos_com_openai", *args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._call_async("gerar_descricao_com_openai", *args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._call_async("gerar_titulos_com_gemini", *args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._call_async("gerar_descricao_com_gemini", *args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._call_async("sugerir_valores_atributos_com_gemini", *args, **kwargs)

    async def call_openai_api(self, *args: Any, **kwargs: Any):
        return await self._call_async("call_openai_api", *args, **kwargs)

    async def call_gemini_api(self, *args: Any, **kwargs: Any):
        return await self._call_async("call_gemini_api", *args, **kwargs)

    async def call_gemini_api_for_suggestions(self, *args: Any, **kwargs: Any):
        return await self._call_async("call_gemini_api_for_suggestions", *args, **kwargs)

    async def get_openai_api_key(self, *args: Any, **kwargs: Any):
        return await self._call_async("get_openai_api_key", *args, **kwargs)

    async def get_gemini_api_key(self, *args: Any, **kwargs: Any):
        return await self._call_async("get_gemini_api_key", *args, **kwargs)
