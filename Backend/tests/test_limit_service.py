"""Module test limit service.

Contains backend logic related to test limit service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest

from Backend.application.services.limit_service import LimitService


class _PortStub:
    """Represent port stub and centralize responsibilities for this module."""
    def __init__(self) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def verificar_limite_uso(self, session, user, tipo_geracao_principal):
        """Run verificar limite uso in this workflow."""
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
        """Run verificar creditos disponiveis geracao ia in this workflow."""
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

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_limit_service_delegates_sync_limit_check():
        """Run test limit service delegates sync limit check in this workflow."""
        port = _PortStub()
        service = LimitService(port=port)
    
        result = service.verificar_limite_uso("db", "user", "titulo")
    
        assert result == {"ok": True}
        assert port.calls[0][0] == "verificar_limite_uso"
        assert port.calls[0][1]["session"] == "db"

    @pytest.mark.asyncio
    async def test_limit_service_delegates_async_credit_check():
        """Run test limit service delegates async credit check in this workflow."""
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


