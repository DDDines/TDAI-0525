"""Module test catalog import finalize service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import pytest

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.catalog_import_finalize_service import (
    CatalogImportFinalizeService,
)


class _OrchestratorStub:
    """Class _OrchestratorStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, plan: TaskExecutionPlan) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.plan = plan
        self.calls = []

    def select_finalize_plan(self, *, command):
        """Execute select_finalize_plan.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append(command)
        return self.plan


class _DispatcherStub:
    """Class _DispatcherStub.

    Encapsulates one responsibility in the backend architecture.
    """
    should_inline = False
    inline_calls = []
    background_calls = []

    @classmethod
    def reset(cls):
        """Execute reset.

        This callable is documented to make behavior explicit for readers.
        """
        cls.inline_calls = []
        cls.background_calls = []

    @classmethod
    def should_run_inline_for_tests(cls, sync_env_var: str):
        """Execute should_run_inline_for_tests.

        This callable is documented to make behavior explicit for readers.
        """
        return cls.should_inline

    @classmethod
    async def run_inline(cls, plan):
        """Execute run_inline.

        This callable is documented to make behavior explicit for readers.
        """
        cls.inline_calls.append(plan)

    @classmethod
    def dispatch_background(cls, background_tasks, plan):
        """Execute dispatch_background.

        This callable is documented to make behavior explicit for readers.
        """
        cls.background_calls.append((background_tasks, plan))


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_command() -> CatalogImportFinalizeCommand:
        """Execute _build_command.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        return CatalogImportFinalizeService(
            oop_executor=object(),
            db_session_factory=lambda: object(),
            dispatcher_cls=_DispatcherStub,
            orchestrator=_OrchestratorStub(plan),
        )

    @pytest.mark.asyncio
    async def test_dispatch_or_run_uses_inline_when_configured():
        """Execute test_dispatch_or_run_uses_inline_when_configured.

        This callable is documented to make behavior explicit for readers.
        """
        executed = []
    
        async def _executor(**kwargs):
            """Execute _executor.

            This callable is documented to make behavior explicit for readers.
            """
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
        """Execute test_dispatch_or_run_uses_background_when_not_inline.

        This callable is documented to make behavior explicit for readers.
        """
        async def _executor(**kwargs):
            """Execute _executor.

            This callable is documented to make behavior explicit for readers.
            """
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
        """Execute test_run_direct_executes_selected_plan.

        This callable is documented to make behavior explicit for readers.
        """
        executed = []
    
        async def _executor(**kwargs):
            """Execute _executor.

            This callable is documented to make behavior explicit for readers.
            """
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








