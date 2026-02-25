from __future__ import annotations

import threading

import pytest
from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.pipeline_dispatcher import PipelineDispatcher


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


def test_dispatch_threaded_executes_plan():
    executed = threading.Event()

    async def _executor_with_event(**kwargs):
        executed.set()
        return kwargs

    plan = TaskExecutionPlan(
        name="test.thread",
        executor_name="dummy",
        executor=_executor_with_event,
        task_kwargs={"file_id": 123},
    )
    PipelineDispatcher.dispatch_threaded(plan, thread_name_prefix="test-pipeline")
    assert executed.wait(timeout=1.5)
