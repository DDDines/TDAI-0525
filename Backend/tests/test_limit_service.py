"""Module test limit service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import pytest

from Backend.application.services.limit_service import LimitService


class _PortStub:
    """Class _PortStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def verificar_limite_uso(self, session, user, tipo_geracao_principal):
        """Execute verificar_limite_uso.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute verificar_creditos_disponiveis_geracao_ia.

        This callable is documented to make behavior explicit for readers.
        """
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

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_limit_service_delegates_sync_limit_check():
        """Execute test_limit_service_delegates_sync_limit_check.

        This callable is documented to make behavior explicit for readers.
        """
        port = _PortStub()
        service = LimitService(port=port)
    
        result = service.verificar_limite_uso("db", "user", "titulo")
    
        assert result == {"ok": True}
        assert port.calls[0][0] == "verificar_limite_uso"
        assert port.calls[0][1]["session"] == "db"

    @pytest.mark.asyncio
    async def test_limit_service_delegates_async_credit_check():
        """Execute test_limit_service_delegates_async_credit_check.

        This callable is documented to make behavior explicit for readers.
        """
        port = _PortStub()
        service = LimitService(port=port)
    
        result = await service.verificar_creditos_disponiveis_geracao_ia(
            session="db",
            user_id=7,
        )
    
        assert result is True
        assert port.calls[0][0] == "verificar_creditos_disponiveis_geracao_ia"
        assert port.calls[0][1]["session"] == "db"
        assert port.calls[0][1]["user_id"] == 7

test_limit_service_delegates_sync_limit_check = _TopLevelFunctionSurface.test_limit_service_delegates_sync_limit_check
test_limit_service_delegates_async_credit_check = _TopLevelFunctionSurface.test_limit_service_delegates_async_credit_check


