"""Module test web enrichment router workflow runtime.

Contains backend logic related to test web enrichment router workflow runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from Backend.routers.web_enrichment import WebEnrichmentRequestService


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_workflow_delega_execucao_task_para_runtime():
        """Run test workflow delega execucao task para runtime in this workflow."""
        called = []
    
        class FakeTaskRunner:
            """Represent fake task runner and centralize responsibilities for this module."""
            async def execute(self, **kwargs):
                """Run execute in this workflow."""
                called.append(("task", kwargs))

        service = WebEnrichmentRequestService()
        service._task_runner = FakeTaskRunner()

        await service.tarefa_enriquecer_produto_web(
            produto_id=10,
            user_id=20,
            termos_busca_override="termo",
            usar_ia=True,
        )
    
        assert called[0][0] == "task"
        assert called[0][1]["produto_id"] == 10
        assert called[0][1]["user_id"] == 20
        assert called[0][1]["termos_busca_override"] == "termo"
        assert called[0][1]["usar_ia"] is True

    def test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime():
        """Run test workflow iniciar enriquecimento usa validacao e dispatch do runtime in this workflow."""
        called = []
    
        class FakeStartService:
            """Represent fake start service and centralize responsibilities for this module."""
            def validate_start_preconditions(self, **kwargs):
                """Validate start preconditions for this workflow."""
                called.append(("validate", kwargs))
            def dispatch_start(self, **kwargs):
                """Dispatch start for this workflow."""
                called.append(("dispatch", kwargs))

        service = WebEnrichmentRequestService()
        service._start_service = FakeStartService()
        user = SimpleNamespace(id=99, is_superuser=False)
        background_tasks = BackgroundTasks()
    
        response = service.iniciar_enriquecimento_produto_web(
            produto_id=77,
            background_tasks=background_tasks,
            current_user=user,
            termos_busca_override="teste",
            usar_ia=False,
        )
    
        assert response["msg"].startswith("Processo de enriquecimento web")
        assert "77" in response["msg"]
    
        validate_call = called[0]
        assert validate_call[0] == "validate"
        assert validate_call[1]["produto_id"] == 77
        assert validate_call[1]["current_user"] is user
    
        dispatch_call = called[1]
        assert dispatch_call[0] == "dispatch"
        command = dispatch_call[1]["command"]
        assert command.produto_id == 77
        assert command.user_id == 99
        assert command.termos_busca_override == "teste"
        assert command.usar_ia is False
        assert dispatch_call[1]["background_tasks"] is background_tasks
        assert callable(dispatch_call[1]["oop_executor"])
        assert "fallback_executor" not in dispatch_call[1]

test_workflow_delega_execucao_task_para_runtime = _TopLevelFunctionSurface.test_workflow_delega_execucao_task_para_runtime
test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime = _TopLevelFunctionSurface.test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime


