from __future__ import annotations

import pytest
from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.pipeline_dispatcher import PipelineDispatcher


class _TopLevelFunctionSurface:

    async def _dummy_executor(**kwargs):
        return kwargs

    def test_should_run_inline_for_tests_with_sync_flag(monkeypatch):
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("CATALOG_IMPORT_TEST_SYNC", "1")
        assert PipelineDispatcher.should_run_inline_for_tests("CATALOG_IMPORT_TEST_SYNC")

    def test_should_not_run_inline_when_no_flags(monkeypatch):
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("CATALOG_IMPORT_TEST_SYNC", raising=False)
        assert not PipelineDispatcher.should_run_inline_for_tests("CATALOG_IMPORT_TEST_SYNC")

    @pytest.mark.asyncio
    async def test_run_inline_executes_plan():
        plan = TaskExecutionPlan(
            name="test.run_inline",
            executor_name="dummy",
            executor=_dummy_executor,
            task_kwargs={"a": 1},
        )
        await PipelineDispatcher.run_inline(plan)

    def test_dispatch_background_schedules_task():
        plan = TaskExecutionPlan(
            name="test.background",
            executor_name="dummy",
            executor=_dummy_executor,
            task_kwargs={"a": 1},
        )
        bg = BackgroundTasks()
        PipelineDispatcher.dispatch_background(bg, plan)
        assert len(bg.tasks) == 1

_dummy_executor = _TopLevelFunctionSurface._dummy_executor
test_should_run_inline_for_tests_with_sync_flag = _TopLevelFunctionSurface.test_should_run_inline_for_tests_with_sync_flag
test_should_not_run_inline_when_no_flags = _TopLevelFunctionSurface.test_should_not_run_inline_when_no_flags
test_run_inline_executes_plan = _TopLevelFunctionSurface.test_run_inline_executes_plan
test_dispatch_background_schedules_task = _TopLevelFunctionSurface.test_dispatch_background_schedules_task










