from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from Backend.routers.web_enrichment import _WebEnrichmentRouterWorkflow


@pytest.mark.asyncio
async def test_workflow_delega_execucao_task_e_oop_para_runtime():
    called = []

    class FakeRuntime:
        async def execute_task(self, **kwargs):
            called.append(("task", kwargs))

        async def execute_oop_task(self, **kwargs):
            called.append(("oop", kwargs))

        def validate_start_preconditions(self, **kwargs):
            called.append(("validate", kwargs))

        def dispatch_start(self, **kwargs):
            called.append(("dispatch", kwargs))

    workflow = _WebEnrichmentRouterWorkflow(runtime=FakeRuntime())

    await workflow.tarefa_enriquecer_produto_web(
        db_session_factory="db_factory",
        produto_id=10,
        user_id=20,
        termos_busca_override="termo",
    )
    await workflow.oop_tarefa_enriquecer_produto_web(produto_id=10, user_id=20)

    assert called[0][0] == "task"
    assert called[0][1]["produto_id"] == 10
    assert called[0][1]["user_id"] == 20
    assert called[0][1]["termos_busca_override"] == "termo"

    assert called[1][0] == "oop"
    assert called[1][1]["produto_id"] == 10
    assert called[1][1]["user_id"] == 20


def test_workflow_iniciar_enriquecimento_usa_validacao_e_dispatch_do_runtime():
    called = []

    class FakeRuntime:
        async def execute_task(self, **kwargs):
            called.append(("task", kwargs))

        async def execute_oop_task(self, **kwargs):
            called.append(("oop", kwargs))

        def validate_start_preconditions(self, **kwargs):
            called.append(("validate", kwargs))

        def dispatch_start(self, **kwargs):
            called.append(("dispatch", kwargs))

    workflow = _WebEnrichmentRouterWorkflow(runtime=FakeRuntime())
    user = SimpleNamespace(id=99)
    background_tasks = BackgroundTasks()

    response = workflow.iniciar_enriquecimento_produto_web(
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
    assert "legacy_executor" not in dispatch_call[1]
