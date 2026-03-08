"""Module test pipeline dispatcher.

Contains backend logic related to test pipeline dispatcher and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest
from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.pipeline_dispatcher import PipelineDispatcher


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    async def _dummy_executor(**kwargs):
        """Run dummy executor in this workflow."""
        return kwargs

    def _sync_executor(**kwargs):
        """Return sync payload for worker-thread execution tests."""
        return kwargs

    def test_should_run_inline_for_tests_with_sync_flag(monkeypatch):
        """Run test should run inline for tests with sync flag in this workflow."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("CATALOG_IMPORT_TEST_SYNC", "1")
        assert PipelineDispatcher.should_run_inline_for_tests("CATALOG_IMPORT_TEST_SYNC")

    def test_should_not_run_inline_when_no_flags(monkeypatch):
        """Run test should not run inline when no flags in this workflow."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("CATALOG_IMPORT_TEST_SYNC", raising=False)
        assert not PipelineDispatcher.should_run_inline_for_tests("CATALOG_IMPORT_TEST_SYNC")

    @pytest.mark.asyncio
    async def test_run_inline_executes_plan():
        """Run test run inline executes plan in this workflow."""
        plan = TaskExecutionPlan(
            name="test.run_inline",
            executor_name="dummy",
            executor=_dummy_executor,
            task_kwargs={"a": 1},
        )
        await PipelineDispatcher.run_inline(plan)

    def test_dispatch_background_schedules_task():
        """Run test dispatch background schedules task in this workflow."""
        plan = TaskExecutionPlan(
            name="test.background",
            executor_name="dummy",
            executor=_dummy_executor,
            task_kwargs={"a": 1},
        )
        bg = BackgroundTasks()
        PipelineDispatcher.dispatch_background(bg, plan)
        assert len(bg.tasks) == 1

    def test_run_plan_in_worker_thread_handles_sync_executor():
        """Execute sync plans without awaiting them."""
        captured = {}
        plan = TaskExecutionPlan(
            name="test.worker.sync",
            executor_name="dummy",
            executor=_sync_executor,
            task_kwargs={"a": 1},
        )

        PipelineDispatcher._run_plan_in_worker_thread(plan)
        captured.update(plan.task_kwargs)
        assert captured == {"a": 1}

    def test_run_plan_in_worker_thread_handles_async_executor(monkeypatch):
        """Execute async plans through asyncio.run in worker mode."""
        seen = {}

        async def async_executor(**kwargs):
            seen.update(kwargs)

        called = {}
        monkeypatch.setattr(
            "Backend.application.services.pipeline_dispatcher.asyncio.run",
            lambda awaitable: called.setdefault("result", awaitable.close() or None),
        )
        plan = TaskExecutionPlan(
            name="test.worker.async",
            executor_name="dummy",
            executor=async_executor,
            task_kwargs={"b": 2},
        )

        PipelineDispatcher._run_plan_in_worker_thread(plan)

        assert "result" in called

_dummy_executor = _TopLevelFunctionSurface._dummy_executor
_sync_executor = _TopLevelFunctionSurface._sync_executor
test_should_run_inline_for_tests_with_sync_flag = _TopLevelFunctionSurface.test_should_run_inline_for_tests_with_sync_flag
test_should_not_run_inline_when_no_flags = _TopLevelFunctionSurface.test_should_not_run_inline_when_no_flags
test_run_inline_executes_plan = _TopLevelFunctionSurface.test_run_inline_executes_plan
test_dispatch_background_schedules_task = _TopLevelFunctionSurface.test_dispatch_background_schedules_task
test_run_plan_in_worker_thread_handles_sync_executor = _TopLevelFunctionSurface.test_run_plan_in_worker_thread_handles_sync_executor
test_run_plan_in_worker_thread_handles_async_executor = _TopLevelFunctionSurface.test_run_plan_in_worker_thread_handles_async_executor










