from __future__ import annotations

import pytest

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.catalog_import_finalize_service import (
    CatalogImportFinalizeService,
)


class _OrchestratorStub:
    def __init__(self, plan: TaskExecutionPlan) -> None:
        self.plan = plan
        self.calls = []

    def select_finalize_plan(self, *, db_session_factory, command):
        self.calls.append((db_session_factory, command))
        return self.plan


class _DispatcherStub:
    should_inline = False
    inline_calls = []
    threaded_calls = []

    @classmethod
    def reset(cls):
        cls.inline_calls = []
        cls.threaded_calls = []

    @classmethod
    def should_run_inline_for_tests(cls, sync_env_var: str):
        return cls.should_inline

    @classmethod
    async def run_inline(cls, plan):
        cls.inline_calls.append(plan)

    @classmethod
    def dispatch_threaded(cls, plan, *, thread_name_prefix: str):
        cls.threaded_calls.append((plan, thread_name_prefix))


class _TopLevelFunctionSurface:

    def _build_command() -> CatalogImportFinalizeCommand:
        return CatalogImportFinalizeCommand(
            file_id=1,
            user_id=2,
            product_type_id=3,
            fornecedor_id=4,
            mapping={"col_0": "nome_base"},
            pages=[1, 2],
            region=[0.0, 0.0, 1.0, 1.0],
        )

    def _build_service(plan: TaskExecutionPlan) -> CatalogImportFinalizeService:
        return CatalogImportFinalizeService(
            oop_executor=object(),
            dispatcher_cls=_DispatcherStub,
            orchestrator=_OrchestratorStub(plan),
        )

    @pytest.mark.asyncio
    async def test_dispatch_or_run_uses_inline_when_configured():
        executed = []
    
        async def _executor(**kwargs):
            executed.append(kwargs)
    
        plan = TaskExecutionPlan(
            name="plan-inline",
            executor_name="exec-inline",
            executor=_executor,
            task_kwargs={"file_id": 1},
        )
        service = _build_service(plan)
        _DispatcherStub.reset()
        _DispatcherStub.should_inline = True
    
        await service.dispatch_or_run(
            background_tasks=object(),
            db_session_factory=lambda: None,
            command=_build_command(),
        )
    
        assert len(_DispatcherStub.inline_calls) == 1
        assert len(_DispatcherStub.threaded_calls) == 0
        assert executed == []

    @pytest.mark.asyncio
    async def test_dispatch_or_run_uses_threaded_when_not_inline():
        async def _executor(**kwargs):
            return None
    
        plan = TaskExecutionPlan(
            name="plan-thread",
            executor_name="exec-thread",
            executor=_executor,
            task_kwargs={"file_id": 2},
        )
        service = _build_service(plan)
        _DispatcherStub.reset()
        _DispatcherStub.should_inline = False
    
        await service.dispatch_or_run(
            background_tasks=object(),
            db_session_factory=lambda: None,
            command=_build_command(),
        )
    
        assert len(_DispatcherStub.inline_calls) == 0
        assert len(_DispatcherStub.threaded_calls) == 1
        assert _DispatcherStub.threaded_calls[0][1] == "catalog-import"

    @pytest.mark.asyncio
    async def test_run_direct_executes_selected_plan():
        executed = []
    
        async def _executor(**kwargs):
            executed.append(kwargs)
    
        plan = TaskExecutionPlan(
            name="plan-direct",
            executor_name="exec-direct",
            executor=_executor,
            task_kwargs={"file_id": 3},
        )
        service = _build_service(plan)
    
        await service.run_direct(
            db_session_factory=lambda: None,
            command=_build_command(),
        )
    
        assert len(executed) == 1
        assert executed[0]["file_id"] == 3

_build_command = _TopLevelFunctionSurface._build_command
_build_service = _TopLevelFunctionSurface._build_service
test_dispatch_or_run_uses_inline_when_configured = _TopLevelFunctionSurface.test_dispatch_or_run_uses_inline_when_configured
test_dispatch_or_run_uses_threaded_when_not_inline = _TopLevelFunctionSurface.test_dispatch_or_run_uses_threaded_when_not_inline
test_run_direct_executes_selected_plan = _TopLevelFunctionSurface.test_run_direct_executes_selected_plan








