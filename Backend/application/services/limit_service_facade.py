from __future__ import annotations

from typing import Any

from Backend.services import limit_service as legacy_limit_service


class LimitServiceFacade:
    """Adaptador OO para o módulo legado de limites/créditos."""

    def __init__(self, legacy_module: Any = legacy_limit_service) -> None:
        self._legacy = legacy_module

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._legacy.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(
        self, *args: Any, **kwargs: Any
    ):
        return await self._legacy.verificar_creditos_disponiveis_geracao_ia(
            *args, **kwargs
        )

    async def verificar_e_consumir_creditos_geracao_ia(
        self, *args: Any, **kwargs: Any
    ):
        return await self._legacy.verificar_e_consumir_creditos_geracao_ia(
            *args, **kwargs
        )

    def __getattr__(self, item: str) -> Any:
        return getattr(self._legacy, item)

