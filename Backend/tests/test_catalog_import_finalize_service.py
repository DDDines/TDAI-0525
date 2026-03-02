"""Module test catalog import finalize service.

Contains backend logic related to test catalog import finalize service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.catalog_import_finalize_service import (
    CatalogImportFinalizeService,
)


class _OrchestratorStub:
    """Represent orchestrator stub and centralize responsibilities for this module."""
    def __init__(self, plan: TaskExecutionPlan) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.plan = plan
        self.calls = []

    def select_finalize_plan(self, *, command):
        """Select finalize plan for this workflow."""
        self.calls.append(command)
        return self.plan


class _DispatcherStub:
    """Represent dispatcher stub and centralize responsibilities for this module."""
    should_inline = False
    inline_calls = []
    background_calls = []

    @classmethod
    def reset(cls):
        """Run reset in this workflow."""
        cls.inline_calls = []
        cls.background_calls = []

    @classmethod
    def should_run_inline_for_tests(cls, sync_env_var: str):
        """Run should run inline for tests in this workflow."""
        return cls.should_inline

    @classmethod
    async def run_inline(cls, plan):
        """Run inline for this workflow."""
        cls.inline_calls.append(plan)

    @classmethod
    def dispatch_background(cls, background_tasks, plan):
        """Dispatch background for this workflow."""
        cls.background_calls.append((background_tasks, plan))


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_command() -> CatalogImportFinalizeCommand:
        """Run build command in this workflow."""
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
        """Run build service in this workflow."""
        return CatalogImportFinalizeService(
            oop_executor=object(),
            dispatcher_cls=_DispatcherStub,
            orchestrator=_OrchestratorStub(plan),
        )

    @pytest.mark.asyncio
    async def test_dispatch_or_run_uses_inline_when_configured():
        """Run test dispatch or run uses inline when configured in this workflow."""
        executed = []
    
        async def _executor(**kwargs):
            """Run executor in this workflow."""
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
            command=_build_command(),
        )
    
        assert len(_DispatcherStub.inline_calls) == 1
        assert len(_DispatcherStub.background_calls) == 0
        assert executed == []

    @pytest.mark.asyncio
    async def test_dispatch_or_run_uses_background_when_not_inline():
        """Run test dispatch or run uses background when not inline in this workflow."""
        async def _executor(**kwargs):
            """Run executor in this workflow."""
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
            command=_build_command(),
        )
    
        assert len(_DispatcherStub.inline_calls) == 0
        assert len(_DispatcherStub.background_calls) == 1
        assert _DispatcherStub.background_calls[0][1] is plan

    @pytest.mark.asyncio
    async def test_run_direct_executes_selected_plan():
        """Run test run direct executes selected plan in this workflow."""
        executed = []
    
        async def _executor(**kwargs):
            """Run executor in this workflow."""
            executed.append(kwargs)
    
        plan = TaskExecutionPlan(
            name="plan-direct",
            executor_name="exec-direct",
            executor=_executor,
            task_kwargs={"file_id": 3},
        )
        service = _build_service(plan)
    
        await service.run_direct(
            command=_build_command(),
        )
    
        assert len(executed) == 1
        assert executed[0]["file_id"] == 3

_build_command = _TopLevelFunctionSurface._build_command
_build_service = _TopLevelFunctionSurface._build_service
test_dispatch_or_run_uses_inline_when_configured = _TopLevelFunctionSurface.test_dispatch_or_run_uses_inline_when_configured
test_dispatch_or_run_uses_background_when_not_inline = _TopLevelFunctionSurface.test_dispatch_or_run_uses_background_when_not_inline
test_run_direct_executes_selected_plan = _TopLevelFunctionSurface.test_run_direct_executes_selected_plan








