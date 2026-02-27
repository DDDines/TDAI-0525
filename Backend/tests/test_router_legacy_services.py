from __future__ import annotations

import pytest

import Backend.routers.historico as historico_router
import Backend.routers.password_recovery as password_recovery_router
import Backend.routers.search as search_router
import Backend.routers.uso_ia as uso_ia_router


def test_historico_legacy_service_delegates_to_workflow(monkeypatch):
    class _WorkflowStub:
        @staticmethod
        def get_tipos_acao():
            return ["CRIACAO", "ATUALIZACAO"]

    monkeypatch.setattr(historico_router, "_historico_workflow", _WorkflowStub())

    result = historico_router.historico_router_legacy_service.get_tipos_acao()

    assert result == ["CRIACAO", "ATUALIZACAO"]


def test_search_legacy_service_delegates_to_workflow(monkeypatch):
    class _WorkflowStub:
        @staticmethod
        def search_all(*_args, **_kwargs):
            return {"results": []}

    monkeypatch.setattr(search_router, "_search_workflow", _WorkflowStub())

    result = search_router.search_router_legacy_service.search_all("db", "user", "q", 10)

    assert result == {"results": []}


def test_uso_ia_legacy_service_delegates_to_workflow(monkeypatch):
    class _WorkflowStub:
        @staticmethod
        def read_usos_ia_por_produto(*_args, **_kwargs):
            return ["ok"]

    monkeypatch.setattr(uso_ia_router, "_uso_ia_workflow", _WorkflowStub())

    result = uso_ia_router.uso_ia_router_legacy_service.read_usos_ia_por_produto(
        "db",
        "user",
        1,
        0,
        10,
    )

    assert result == ["ok"]


@pytest.mark.asyncio
async def test_password_recovery_legacy_service_delegates_async(monkeypatch):
    class _WorkflowStub:
        @staticmethod
        async def recover_password(*_args, **_kwargs):
            return {"msg": "ok"}

        @staticmethod
        def reset_password(*_args, **_kwargs):
            return {"msg": "reset"}

    monkeypatch.setattr(password_recovery_router, "_password_recovery_workflow", _WorkflowStub())

    recover_result = await password_recovery_router.password_recovery_router_legacy_service.recover_password(
        "db",
        "test@example.com",
        "request",
    )
    reset_result = password_recovery_router.password_recovery_router_legacy_service.reset_password(
        "db",
        "payload",
    )

    assert recover_result == {"msg": "ok"}
    assert reset_result == {"msg": "reset"}
