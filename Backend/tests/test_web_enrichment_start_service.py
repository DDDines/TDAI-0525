"""Module test web enrichment start service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.web_enrichment_start_service import (
    WebEnrichmentStartService,
)


class _CrudProdutosStub:
    """Class _CrudProdutosStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, produto=None):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.produto = produto

    def get_produto(self, *, produto_id: int):
        """Execute get_produto.

        This callable is documented to make behavior explicit for readers.
        """
        _ = produto_id
        return self.produto


class _ModelsStub:
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    class StatusEnriquecimentoEnum:
        """Class StatusEnriquecimentoEnum.

        Encapsulates one responsibility in the backend architecture.
        """
        EM_PROGRESSO = "EM_PROGRESSO"


class _DispatcherStub:
    """Class _DispatcherStub.

    Encapsulates one responsibility in the backend architecture.
    """
    dispatched = []

    @classmethod
    def reset(cls):
        """Execute reset.

        This callable is documented to make behavior explicit for readers.
        """
        cls.dispatched = []

    @classmethod
    def dispatch_background(cls, background_tasks, plan):
        """Execute dispatch_background.

        This callable is documented to make behavior explicit for readers.
        """
        cls.dispatched.append((background_tasks, plan))


class _OrchestratorStub:
    """Class _OrchestratorStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *args, **kwargs):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (args, kwargs)
        self.calls = []

    def select_start_plan(self, *, command):
        """Execute select_start_plan.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append(command)

        async def _executor(**kwargs):
            """Execute _executor.

            This callable is documented to make behavior explicit for readers.
            """
            return kwargs

        return TaskExecutionPlan(
            name="web-enrichment-plan",
            executor_name="executor",
            executor=_executor,
            task_kwargs={"produto_id": command.produto_id},
        )


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(produto=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        return WebEnrichmentStartService(
            product_repository=_CrudProdutosStub(produto=produto),
            models=_ModelsStub,
            dispatcher_cls=_DispatcherStub,
            orchestrator_cls=_OrchestratorStub,
        )

    def test_validate_start_preconditions_not_found():
        """Execute test_validate_start_preconditions_not_found.

        This callable is documented to make behavior explicit for readers.
        """
        service = _build_service(produto=None)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 404

    def test_validate_start_preconditions_forbidden():
        """Execute test_validate_start_preconditions_forbidden.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(user_id=2, status_enriquecimento_web="PENDENTE")
        service = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 403

    def test_validate_start_preconditions_conflict():
        """Execute test_validate_start_preconditions_conflict.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="EM_PROGRESSO")
        service = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 409

    def test_validate_start_preconditions_success():
        """Execute test_validate_start_preconditions_success.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="PENDENTE")
        service = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        service.validate_start_preconditions(
            produto_id=10,
            current_user=user,
        )

    def test_dispatch_start_selects_and_dispatches():
        """Execute test_dispatch_start_selects_and_dispatches.

        This callable is documented to make behavior explicit for readers.
        """
        _DispatcherStub.reset()
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="PENDENTE")
        service = _build_service(produto=produto)
        command = SimpleNamespace(produto_id=7, user_id=1, termos_busca_override=None)
    
        plan = service.dispatch_start(
            background_tasks=object(),
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










