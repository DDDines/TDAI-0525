"""Module test web enrichment start service.

Contains backend logic related to test web enrichment start service and documents its role in the OOP architecture.
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
    """Represent crud produtos stub and centralize responsibilities for this module."""
    def __init__(self, produto=None):
        """Initialize collaborators and configuration required by this component."""
        self.produto = produto
        self.status_updates = []

    def get_produto(self, *, produto_id: int, user_id=None):
        """Return produto for this workflow."""
        _ = produto_id
        return self.produto

    def set_web_enrichment_status(self, *, produto_id: int, status: str, log_message: str | None = None):
        """Persist status updates captured for assertions in tests."""
        self.status_updates.append((produto_id, status, log_message))
        return self.produto


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    class StatusEnriquecimentoEnum:
        """Represent status enriquecimento enum and centralize responsibilities for this module."""
        EM_PROGRESSO = "EM_PROGRESSO"
        PENDENTE = "PENDENTE"


class _DispatcherStub:
    """Represent dispatcher stub and centralize responsibilities for this module."""
    dispatched = []

    @classmethod
    def reset(cls):
        """Run reset in this workflow."""
        cls.dispatched = []

    @classmethod
    def dispatch_background(cls, background_tasks, plan):
        """Dispatch background for this workflow."""
        cls.dispatched.append((background_tasks, plan))


class _OrchestratorStub:
    """Represent orchestrator stub and centralize responsibilities for this module."""
    def __init__(self, *args, **kwargs):
        """Initialize collaborators and configuration required by this component."""
        _ = (args, kwargs)
        self.calls = []

    def select_start_plan(self, *, command):
        """Select start plan for this workflow."""
        self.calls.append(command)

        async def _executor(**kwargs):
            """Run executor in this workflow."""
            return kwargs

        return TaskExecutionPlan(
            name="web-enrichment-plan",
            executor_name="executor",
            executor=_executor,
            task_kwargs={"produto_id": command.produto_id},
        )


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(produto=None):
        """Run build service in this workflow."""
        repo = _CrudProdutosStub(produto=produto)
        return WebEnrichmentStartService(
            product_repository=repo,
            models=_ModelsStub,
            dispatcher_cls=_DispatcherStub,
            orchestrator_cls=_OrchestratorStub,
        ), repo

    def test_validate_start_preconditions_not_found():
        """Run test validate start preconditions not found in this workflow."""
        service, _ = _build_service(produto=None)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 404

    def test_validate_start_preconditions_forbidden():
        """Run test validate start preconditions forbidden in this workflow."""
        produto = SimpleNamespace(user_id=2, status_enriquecimento_web="PENDENTE")
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 403

    def test_validate_start_preconditions_conflict():
        """Run test validate start preconditions conflict in this workflow."""
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="EM_PROGRESSO")
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 409

    def test_validate_start_preconditions_success():
        """Run test validate start preconditions success in this workflow."""
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="PENDENTE")
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        service.validate_start_preconditions(
            produto_id=10,
            current_user=user,
        )

    def test_validate_start_preconditions_blocks_ai_without_product_type():
        """Run test validate start preconditions blocks ai without product type in this workflow."""
        produto = SimpleNamespace(
            user_id=1,
            status_enriquecimento_web="PENDENTE",
            product_type_id=None,
        )
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)

        with pytest.raises(HTTPException) as exc:
            service.validate_start_preconditions(
                produto_id=10,
                current_user=user,
                usar_ia=True,
            )

        assert exc.value.status_code == 400
        assert "tipo de produto" in exc.value.detail.lower()

    def test_dispatch_start_selects_and_dispatches():
        """Run test dispatch start selects and dispatches in this workflow."""
        _DispatcherStub.reset()
        produto = SimpleNamespace(user_id=1, status_enriquecimento_web="PENDENTE")
        service, repo = _build_service(produto=produto)
        command = SimpleNamespace(produto_id=7, user_id=1, termos_busca_override=None)
    
        plan = service.dispatch_start(
            background_tasks=object(),
            command=command,
            oop_executor=object(),
        )
    
        assert plan.task_kwargs["produto_id"] == 7
        assert len(_DispatcherStub.dispatched) == 1
        assert repo.status_updates == [
            (7, _ModelsStub.StatusEnriquecimentoEnum.PENDENTE, "Enriquecimento web enfileirado para execucao.")
        ]

_build_service = _TopLevelFunctionSurface._build_service
test_validate_start_preconditions_not_found = _TopLevelFunctionSurface.test_validate_start_preconditions_not_found
test_validate_start_preconditions_forbidden = _TopLevelFunctionSurface.test_validate_start_preconditions_forbidden
test_validate_start_preconditions_conflict = _TopLevelFunctionSurface.test_validate_start_preconditions_conflict
test_validate_start_preconditions_success = _TopLevelFunctionSurface.test_validate_start_preconditions_success
test_validate_start_preconditions_blocks_ai_without_product_type = _TopLevelFunctionSurface.test_validate_start_preconditions_blocks_ai_without_product_type
test_dispatch_start_selects_and_dispatches = _TopLevelFunctionSurface.test_dispatch_start_selects_and_dispatches










