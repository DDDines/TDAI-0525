from __future__ import annotations

from typing import Any, Optional

from Backend.core.legacy_guard import assert_legacy_usage_allowed
from Backend.services import limit_service


class LegacyLimitBridge:
    """Bridge explicito para o modulo legado de limites."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or limit_service

    @staticmethod
    def _assert_legacy_allowed() -> None:
        assert_legacy_usage_allowed("Backend.infrastructure.legacy.LegacyLimitBridge")

    def _call(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return getattr(self._module, method_name)(*args, **kwargs)

    async def _call_async(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return await getattr(self._module, method_name)(*args, **kwargs)

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._call("verificar_limite_uso", *args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._call_async("verificar_creditos_disponiveis_geracao_ia", *args, **kwargs)

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._call_async("verificar_e_consumir_creditos_geracao_ia", *args, **kwargs)
