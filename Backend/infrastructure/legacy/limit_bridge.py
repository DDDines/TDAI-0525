from __future__ import annotations

from typing import Any, Optional

from Backend.services import limit_service


class LegacyLimitBridge:
    """Bridge explicito para o modulo legado de limites."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or limit_service

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._module.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._module.verificar_creditos_disponiveis_geracao_ia(*args, **kwargs)

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._module.verificar_e_consumir_creditos_geracao_ia(*args, **kwargs)
