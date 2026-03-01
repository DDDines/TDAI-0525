from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.web_enrichment_start_service import (
    WebEnrichmentStartService,
)


class _CrudProdutosStub:
    def __init__(self, produto=None):
        self.produto = produto

    def get_produto(self, db, *, produto_id: int):
        _ = (db, produto_id)
        return self.produto


class _ModelsStub:
    class StatusEnriquecimentoEnum:
        EM_PROGRESSO = "EM_PROGRESSO"


class _DispatcherStub:
    dispatched = []

    @classmethod
    def reset(cls):
        cls.dispatched = []

    @classmethod
    def dispatch_background(cls, background_tasks, plan):
        cls.dispatched.append((background_tasks, plan))


class _OrchestratorStub:
    def __init__(self, *args, **kwargs):
        _ = (args, kwargs)
        self.calls = []

    def select_start_plan(self, *, db_session_factory, command):
        self.calls.append((db_session_factory, command))

        async def _executor(**kwargs):
            return kwargs

        return TaskExecutionPlan(
            name="web-enrichment-plan",
            executor_name="executor",
            executor=_executor,
            task_kwargs={"produto_id": command.produto_id},
        )


class _TopLevelFunctionSurface:

    def _build_service(produto=None):
        return WebEnrichmentStartService(
            product_repository=_CrudProdutosStub(produto=produto),
            models=_ModelsStub,
            dispatcher_cls=_DispatcherStub,
            orchestrator_cls=_OrchestratorStub,
        )

    def test_validate_start_preconditions_not_found():
        service = _build_service(produto=None)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                product_repo=_CrudProdutosStub(produto=None),
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 404

    def test_validate_start_preconditions_forbidden():
        produto = SimpleNamespace(user_id=2, status_enriquecimento_web="PENDENTE")
        service = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                product_repo=_CrudProdutosStub(produto=produto),
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 403

    def test_validate_start_preconditions_conflict():
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="EM_PROGRESSO")
        service = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                product_repo=_CrudProdutosStub(produto=produto),
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 409

    def test_validate_start_preconditions_success():
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="PENDENTE")
        service = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        service.validate_start_preconditions(
            product_repo=_CrudProdutosStub(produto=produto),
            produto_id=10,
            current_user=user,
        )

    def test_dispatch_start_selects_and_dispatches():
        _DispatcherStub.reset()
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="PENDENTE")
        service = _build_service(produto=produto)
        command = SimpleNamespace(produto_id=7, user_id=1, termos_busca_override=None)
    
        plan = service.dispatch_start(
            background_tasks=object(),
            db_session_factory=lambda: object(),
            command=command,
            oop_executor=object(),
        )
    
        assert plan.task_kwargs["produto_id"] == 7
        assert len(_DispatcherStub.dispatched) == 1

_build_service = _TopLevelFunctionSurface._build_service
test_validate_start_preconditions_not_found = _TopLevelFunctionSurface.test_validate_start_preconditions_not_found
test_validate_start_preconditions_forbidden = _TopLevelFunctionSurface.test_validate_start_preconditions_forbidden
test_validate_start_preconditions_conflict = _TopLevelFunctionSurface.test_validate_start_preconditions_conflict
test_validate_start_preconditions_success = _TopLevelFunctionSurface.test_validate_start_preconditions_success
test_dispatch_start_selects_and_dispatches = _TopLevelFunctionSurface.test_dispatch_start_selects_and_dispatches










