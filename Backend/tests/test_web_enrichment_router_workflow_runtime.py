from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from Backend.routers.web_enrichment import WebEnrichmentRequestService


class _TopLevelFunctionSurface:

    @pytest.mark.asyncio
    async def test_workflow_delega_execucao_task_para_runtime():
        called = []
    
        class FakeTaskRunner:
            async def execute(self, **kwargs):
                called.append(("task", kwargs))

        service = WebEnrichmentRequestService()
        service._task_runner = FakeTaskRunner()

        await service.tarefa_enriquecer_produto_web(
            db_session_factory="db_factory",
            produto_id=10,
            user_id=20,
            termos_busca_override="termo",
        )
    
        assert called[0][0] == "task"
        assert called[0][1]["produto_id"] == 10
        assert called[0][1]["user_id"] == 20
        assert called[0][1]["termos_busca_override"] == "termo"

    def test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime():
        called = []
    
        class FakeStartService:
            def validate_start_preconditions(self, **kwargs):
                called.append(("validate", kwargs))
            def dispatch_start(self, **kwargs):
                called.append(("dispatch", kwargs))

        service = WebEnrichmentRequestService()
        service._start_service = FakeStartService()
        user = SimpleNamespace(id=99)
        background_tasks = BackgroundTasks()
    
        response = service.iniciar_enriquecimento_produto_web(
            produto_id=77,
            background_tasks=background_tasks,
            current_user=user,
            termos_busca_override="teste",
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
        assert dispatch_call[1]["background_tasks"] is background_tasks
        assert callable(dispatch_call[1]["oop_executor"])
        assert "fallback_executor" not in dispatch_call[1]

test_workflow_delega_execucao_task_para_runtime = _TopLevelFunctionSurface.test_workflow_delega_execucao_task_para_runtime
test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime = _TopLevelFunctionSurface.test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime


