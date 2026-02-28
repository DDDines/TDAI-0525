from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules import limit_module


class LimitRuntimeService:
    """Explicit runtime service surface for limits and credits flows."""

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return limit_module.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await limit_module.verificar_creditos_disponiveis_geracao_ia(
            *args,
            **kwargs,
        )

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await limit_module.verificar_e_consumir_creditos_geracao_ia(
            *args,
            **kwargs,
        )


limit_runtime_service = LimitRuntimeService()

