from __future__ import annotations

import pytest

from Backend.application.services.limit_service_facade import LimitServiceFacade


class _LegacyLimitStub:
    def __init__(self) -> None:
        self.calls = []

    def verificar_limite_uso(self, session, user, tipo_geracao_principal):
        self.calls.append(
            (
                "verificar_limite_uso",
                {
                    "session": session,
                    "user": user,
                    "tipo_geracao_principal": tipo_geracao_principal,
                },
            )
        )
        return {"ok": True}

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        session,
        user_id,
        creditos_necessarios=1,
    ):
        self.calls.append(
            (
                "verificar_creditos_disponiveis_geracao_ia",
                {
                    "session": session,
                    "user_id": user_id,
                    "creditos_necessarios": creditos_necessarios,
                },
            )
        )
        return True


class _TopLevelFunctionSurface:

    def test_limit_service_facade_delegates_sync_limit_check():
        legacy = _LegacyLimitStub()
        facade = LimitServiceFacade(port=legacy)
    
        result = facade.verificar_limite_uso("db", "user", "titulo")
    
        assert result == {"ok": True}
        assert legacy.calls[0][0] == "verificar_limite_uso"
        assert legacy.calls[0][1]["session"] == "db"

    @pytest.mark.asyncio
    async def test_limit_service_facade_delegates_async_credit_check():
        legacy = _LegacyLimitStub()
        facade = LimitServiceFacade(port=legacy)
    
        result = await facade.verificar_creditos_disponiveis_geracao_ia(
            session="db",
            user_id=11,
        )
    
        assert result is True
        assert legacy.calls[0][0] == "verificar_creditos_disponiveis_geracao_ia"
        assert legacy.calls[0][1]["session"] == "db"
        assert legacy.calls[0][1]["user_id"] == 11

test_limit_service_facade_delegates_sync_limit_check = _TopLevelFunctionSurface.test_limit_service_facade_delegates_sync_limit_check
test_limit_service_facade_delegates_async_credit_check = _TopLevelFunctionSurface.test_limit_service_facade_delegates_async_credit_check


