from __future__ import annotations

from typing import Any, Optional

from Backend.services import ia_generation_service


class LegacyIAGenerationBridge:
    """Bridge explicito para o modulo legado de geracao IA."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or ia_generation_service

    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any):
        return await self._module.gerar_titulos_com_openai(*args, **kwargs)

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any):
        return await self._module.gerar_descricao_com_openai(*args, **kwargs)

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._module.gerar_titulos_com_gemini(*args, **kwargs)

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._module.gerar_descricao_com_gemini(*args, **kwargs)

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any):
        return await self._module.sugerir_valores_atributos_com_gemini(*args, **kwargs)

    async def call_openai_api(self, *args: Any, **kwargs: Any):
        return await self._module.call_openai_api(*args, **kwargs)

    async def call_gemini_api(self, *args: Any, **kwargs: Any):
        return await self._module.call_gemini_api(*args, **kwargs)

    async def call_gemini_api_for_suggestions(self, *args: Any, **kwargs: Any):
        return await self._module.call_gemini_api_for_suggestions(*args, **kwargs)

    async def get_openai_api_key(self, *args: Any, **kwargs: Any):
        return await self._module.get_openai_api_key(*args, **kwargs)

    async def get_gemini_api_key(self, *args: Any, **kwargs: Any):
        return await self._module.get_gemini_api_key(*args, **kwargs)
