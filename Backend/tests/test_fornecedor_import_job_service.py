"""Module test fornecedor import job service.

Contains backend logic related to test fornecedor import job service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_import_job_service import (
    FornecedorImportJobService,
)


class _CrudFornecedorImportJobsStub:
    """Represent crud fornecedor import jobs stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.job = None
        self.updated_status = None

    def get_import_job(self, job_id):
        """Return import job for this workflow."""
        if self.job and self.job.id == job_id:
            return self.job
        return None

    def update_job_status(self, job, status):
        """Update job status for this workflow."""
        job.status = status
        self.updated_status = status
        return job


class _CrudProdutosStub:
    """Represent crud produtos stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def get_or_create_produto(self, *, produto, user_id):
        """Return or create produto for this workflow."""
        self.calls.append((self._db, produto.payload, user_id))
        return SimpleNamespace(id=len(self.calls))

    def bind(self, db):
        """Run bind in this workflow."""
        self._db = db
        return self


class _ProdutoCreateSchemaStub:
    """Represent produto create schema stub and centralize responsibilities for this module."""
    def __init__(self, **payload):
        """Initialize collaborators and configuration required by this component."""
        if not payload.get("nome_base"):
            raise ValueError("nome_base obrigatorio")
        self.payload = payload


class _DbSessionStub:
    """Represent db session stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.closed = False

    def get_bind(self):
        """Return bind for this workflow."""
        return object()

    def close(self):
        """Run close in this workflow."""
        self.closed = True


class _BackgroundTasksStub:
    """Represent background tasks stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.added = []

    def add_task(self, fn, **kwargs):
        """Run add task in this workflow."""
        self.added.append((fn, kwargs))


class _DispatcherStub:
    """Represent dispatcher stub and centralize responsibilities for this module."""

    def __init__(self, *, use_celery: bool):
        """Initialize collaborators and configuration required by this component."""
        self._use_celery = use_celery
        self.named_calls = []

    def uses_celery(self):
        """Return whether this dispatcher emulates Celery."""
        return self._use_celery

    def dispatch_named_task(self, *, task_name, task_kwargs):
        """Capture Celery task dispatches."""
        self.named_calls.append((task_name, task_kwargs))
        return "async-result"

    def dispatch_named_or_background(self, *, background_tasks, task_name, task_kwargs, fallback_callable):
        """Mirror the real dispatcher interface used by the service."""
        if self._use_celery:
            return self.dispatch_named_task(task_name=task_name, task_kwargs=task_kwargs)
        background_tasks.add_task(fallback_callable, **task_kwargs)
        return None


class _SessionProviderStub:
    """Simple OO provider that opens sessions from a factory."""

    def __init__(self, factory):
        """Store session factory callable used by tests."""
        self._factory = factory

    def open_session(self):
        """Open and return a session instance."""
        return self._factory()


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, job, session_provider=None, dispatcher_cls=None):
        """Run build service in this workflow."""
        crud_jobs = _CrudFornecedorImportJobsStub()
        crud_jobs.job = job
        crud_produtos = _CrudProdutosStub()
    
        class _ImportJobRepoClass:
            """Represent import job repo class and centralize responsibilities for this module."""
            def __init__(self, db):
                """Initialize collaborators and configuration required by this component."""
                _ = db
                self._stub = crud_jobs
    
            def get_import_job(self, job_id):
                """Return import job for this workflow."""
                return self._stub.get_import_job(job_id)
    
            def update_job_status(self, job, status):
                """Update job status for this workflow."""
                return self._stub.update_job_status(job, status)
    
        class _ProdutoRepoClass:
            """Represent produto repo class and centralize responsibilities for this module."""
            def __init__(self, db):
                """Initialize collaborators and configuration required by this component."""
                self._stub = crud_produtos.bind(db)
    
            def get_or_create_produto(self, *, produto, user_id):
                """Return or create produto for this workflow."""
                return self._stub.get_or_create_produto(produto=produto, user_id=user_id)
    
        service = FornecedorImportJobService(
            session_provider=session_provider or _SessionProviderStub(lambda: _DbSessionStub()),
            import_job_repository_factory=_ImportJobRepoClass,
            produto_repository_factory=_ProdutoRepoClass,
            produto_create_schema=_ProdutoCreateSchemaStub,
            dispatcher_cls=dispatcher_cls or (lambda: _DispatcherStub(use_celery=False)),
        )
        return service, crud_jobs, crud_produtos

    def test_get_job_for_user_or_404_returns_job():
        """Run test get job for user or 404 returns job in this workflow."""
        job = SimpleNamespace(id=5, user_id=10, result_summary=[])
        service, _, _ = _build_service(job=job)
    
        found = service.get_job_for_user_or_404(job_id=5, user_id=10)
    
        assert found is job

    def test_get_job_for_user_or_404_raises_for_invalid_user():
        """Run test get job for user or 404 raises for invalid user in this workflow."""
        job = SimpleNamespace(id=5, user_id=10, result_summary=[])
        service, _, _ = _build_service(job=job)
    
        with pytest.raises(HTTPException) as exc:
            service.get_job_for_user_or_404(job_id=5, user_id=99)
    
        assert exc.value.status_code == 404

    def test_schedule_commit_adds_background_task():
        """Run test schedule commit adds background task in this workflow."""
        job = SimpleNamespace(id=5, user_id=10, result_summary=[])
        service, _, _ = _build_service(job=job)
        background = _BackgroundTasksStub()
    
        service.schedule_commit(
            background_tasks=background,
            job_id=5,
            user_id=10,
        )
    
        assert len(background.added) == 1
        task_fn, kwargs = background.added[0]
        assert task_fn == service.commit_job_task
        assert kwargs["job_id"] == 5

    def test_schedule_commit_dispatches_celery_when_enabled():
        """Dispatch import commit through Celery when configured."""
        job = SimpleNamespace(id=5, user_id=10, result_summary=[])
        dispatcher = _DispatcherStub(use_celery=True)
        service, _, _ = _build_service(
            job=job,
            dispatcher_cls=lambda: dispatcher,
        )

        service.schedule_commit(
            background_tasks=_BackgroundTasksStub(),
            job_id=5,
            user_id=10,
        )

        assert dispatcher.named_calls == [
            ("fornecedor_import.commit", {"job_id": 5, "user_id": 10})
        ]

    def test_commit_job_task_processes_valid_rows_and_marks_completed():
        """Run test commit job task processes valid rows and marks completed in this workflow."""
        job = SimpleNamespace(
            id=5,
            user_id=10,
            status="REVIEW",
            result_summary=[
                {"nome_base": "Produto A", "sku_original": "SKU-A"},
                {"nome_base": "Produto B"},
                {"sku_original": "sem_nome"},
                "invalido",
            ],
        )
        db_instance = _DbSessionStub()

        def _factory():
            """Run factory in this workflow."""
            return db_instance

        service, crud_jobs, crud_produtos = _build_service(
            job=job,
            session_provider=_SessionProviderStub(_factory),
        )
    
        service.commit_job_task(job_id=5, user_id=10)
    
        assert len(crud_produtos.calls) == 2
        assert crud_jobs.updated_status == "COMPLETED"
        assert db_instance.closed is True

    def test_commit_job_task_accepts_summary_dict_with_produtos():
        """Run test commit job task accepts summary dict with produtos in this workflow."""
        job = SimpleNamespace(
            id=6,
            user_id=10,
            status="REVIEW",
            result_summary={
                "produtos": [
                    {"nome_base": "Produto C"},
                    {"nome_base": "Produto D"},
                ]
            },
        )
        db_instance = _DbSessionStub()

        service, crud_jobs, crud_produtos = _build_service(
            job=job,
            session_provider=_SessionProviderStub(lambda: db_instance),
        )

        service.commit_job_task(job_id=6, user_id=10)
    
        assert len(crud_produtos.calls) == 2
        assert crud_jobs.updated_status == "COMPLETED"

_build_service = _TopLevelFunctionSurface._build_service
test_get_job_for_user_or_404_returns_job = _TopLevelFunctionSurface.test_get_job_for_user_or_404_returns_job
test_get_job_for_user_or_404_raises_for_invalid_user = _TopLevelFunctionSurface.test_get_job_for_user_or_404_raises_for_invalid_user
test_schedule_commit_adds_background_task = _TopLevelFunctionSurface.test_schedule_commit_adds_background_task
test_schedule_commit_dispatches_celery_when_enabled = _TopLevelFunctionSurface.test_schedule_commit_dispatches_celery_when_enabled
test_commit_job_task_processes_valid_rows_and_marks_completed = _TopLevelFunctionSurface.test_commit_job_task_processes_valid_rows_and_marks_completed
test_commit_job_task_accepts_summary_dict_with_produtos = _TopLevelFunctionSurface.test_commit_job_task_accepts_summary_dict_with_produtos










