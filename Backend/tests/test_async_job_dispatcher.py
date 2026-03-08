"""Tests for the async job dispatcher abstraction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.services.async_job_dispatcher import AsyncJobDispatcher


class _BackgroundTasksStub:
    def __init__(self):
        self.calls = []

    def add_task(self, fn, **kwargs):
        self.calls.append((fn, kwargs))


class _TaskStub:
    def __init__(self):
        self.calls = []

    def delay(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(id="task-123")


def test_async_job_dispatcher_uses_celery_flag():
    dispatcher = AsyncJobDispatcher(
        settings_obj=SimpleNamespace(ASYNC_DISPATCH_PROVIDER="celery"),
        task_resolver=lambda _name: _TaskStub(),
    )

    assert dispatcher.uses_celery() is True


def test_async_job_dispatcher_dispatches_named_task():
    task = _TaskStub()
    dispatcher = AsyncJobDispatcher(
        settings_obj=SimpleNamespace(ASYNC_DISPATCH_PROVIDER="celery"),
        task_resolver=lambda _name: task,
    )

    result = dispatcher.dispatch_named_task(
        task_name="generation.run",
        task_kwargs={"produto_id": 7},
    )

    assert result.id == "task-123"
    assert task.calls == [{"produto_id": 7}]


def test_async_job_dispatcher_dispatches_background_when_celery_disabled():
    background = _BackgroundTasksStub()
    dispatcher = AsyncJobDispatcher(
        settings_obj=SimpleNamespace(ASYNC_DISPATCH_PROVIDER="background_tasks"),
        task_resolver=lambda _name: _TaskStub(),
    )
    called = []

    def _fallback(**kwargs):
        called.append(kwargs)

    result = dispatcher.dispatch_named_or_background(
        background_tasks=background,
        task_name="pdf_extraction.page",
        task_kwargs={"page_number": 2},
        fallback_callable=_fallback,
    )

    assert result is None
    assert called == []
    assert background.calls == [(_fallback, {"page_number": 2})]


def test_async_job_dispatcher_dispatches_named_or_background_via_celery():
    background = _BackgroundTasksStub()
    task = _TaskStub()
    dispatcher = AsyncJobDispatcher(
        settings_obj=SimpleNamespace(ASYNC_DISPATCH_PROVIDER="celery"),
        task_resolver=lambda _name: task,
    )

    result = dispatcher.dispatch_named_or_background(
        background_tasks=background,
        task_name="pdf_extraction.page",
        task_kwargs={"page_number": 3},
        fallback_callable=lambda **kwargs: kwargs,
    )

    assert result.id == "task-123"
    assert task.calls == [{"page_number": 3}]
    assert background.calls == []


def test_async_job_dispatcher_uses_default_task_resolver(monkeypatch):
    task = _TaskStub()
    imported = []

    class _Module:
        @staticmethod
        def resolve_task(name):
            imported.append(name)
            return task

    monkeypatch.setattr(
        "Backend.application.services.async_job_dispatcher.importlib.import_module",
        lambda _name: _Module,
    )

    dispatcher = AsyncJobDispatcher(
        settings_obj=SimpleNamespace(ASYNC_DISPATCH_PROVIDER="celery"),
    )
    result = dispatcher.dispatch_named_task(
        task_name="web_enrichment.start",
        task_kwargs={"produto_id": 9},
    )

    assert result.id == "task-123"
    assert imported == ["web_enrichment.start"]


def test_async_job_dispatcher_raises_when_task_missing():
    dispatcher = AsyncJobDispatcher(
        settings_obj=SimpleNamespace(ASYNC_DISPATCH_PROVIDER="celery"),
        task_resolver=lambda _name: (_ for _ in ()).throw(LookupError("missing")),
    )

    with pytest.raises(LookupError):
        dispatcher.dispatch_named_task(task_name="missing", task_kwargs={})
