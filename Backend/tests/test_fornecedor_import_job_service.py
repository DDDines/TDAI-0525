from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_import_job_service import (
    FornecedorImportJobService,
)


class _CrudFornecedorImportJobsStub:
    def __init__(self):
        self.job = None
        self.updated_status = None

    def get_import_job(self, job_id):
        if self.job and self.job.id == job_id:
            return self.job
        return None

    def update_job_status(self, job, status):
        job.status = status
        self.updated_status = status
        return job


class _CrudProdutosStub:
    def __init__(self):
        self.calls = []

    def get_or_create_produto(self, *, produto, user_id):
        self.calls.append((self._db, produto.payload, user_id))
        return SimpleNamespace(id=len(self.calls))

    def bind(self, db):
        self._db = db
        return self


class _ProdutoCreateSchemaStub:
    def __init__(self, **payload):
        if not payload.get("nome_base"):
            raise ValueError("nome_base obrigatorio")
        self.payload = payload


class _DbSessionStub:
    def __init__(self):
        self.closed = False

    def get_bind(self):
        return object()

    def close(self):
        self.closed = True


class _BackgroundTasksStub:
    def __init__(self):
        self.added = []

    def add_task(self, fn, **kwargs):
        self.added.append((fn, kwargs))


class _TopLevelFunctionSurface:

    def _build_service(*, job, db_session_factory=None):
        crud_jobs = _CrudFornecedorImportJobsStub()
        crud_jobs.job = job
        crud_produtos = _CrudProdutosStub()
    
        class _ImportJobRepoClass:
            def __init__(self, db):
                _ = db
                self._stub = crud_jobs
    
            def get_import_job(self, job_id):
                return self._stub.get_import_job(job_id)
    
            def update_job_status(self, job, status):
                return self._stub.update_job_status(job, status)
    
        class _ProdutoRepoClass:
            def __init__(self, db):
                self._stub = crud_produtos.bind(db)
    
            def get_or_create_produto(self, *, produto, user_id):
                return self._stub.get_or_create_produto(produto=produto, user_id=user_id)
    
        service = FornecedorImportJobService(
            db_session_factory=db_session_factory or (lambda: _DbSessionStub()),
            import_job_repository_cls=_ImportJobRepoClass,
            produto_repository_cls=_ProdutoRepoClass,
            produto_create_schema=_ProdutoCreateSchemaStub,
        )
        return service, crud_jobs, crud_produtos

    def test_get_job_for_user_or_404_returns_job():
        job = SimpleNamespace(id=5, user_id=10, result_summary=[])
        service, _, _ = _build_service(job=job)
    
        found = service.get_job_for_user_or_404(job_id=5, user_id=10)
    
        assert found is job

    def test_get_job_for_user_or_404_raises_for_invalid_user():
        job = SimpleNamespace(id=5, user_id=10, result_summary=[])
        service, _, _ = _build_service(job=job)
    
        with pytest.raises(HTTPException) as exc:
            service.get_job_for_user_or_404(job_id=5, user_id=99)
    
        assert exc.value.status_code == 404

    def test_schedule_commit_adds_background_task():
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

    def test_commit_job_task_processes_valid_rows_and_marks_completed():
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
            return db_instance

        service, crud_jobs, crud_produtos = _build_service(
            job=job,
            db_session_factory=_factory,
        )
    
        service.commit_job_task(job_id=5, user_id=10)
    
        assert len(crud_produtos.calls) == 2
        assert crud_jobs.updated_status == "COMPLETED"
        assert db_instance.closed is True

    def test_commit_job_task_accepts_summary_dict_with_produtos():
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
            db_session_factory=lambda: db_instance,
        )

        service.commit_job_task(job_id=6, user_id=10)
    
        assert len(crud_produtos.calls) == 2
        assert crud_jobs.updated_status == "COMPLETED"

_build_service = _TopLevelFunctionSurface._build_service
test_get_job_for_user_or_404_returns_job = _TopLevelFunctionSurface.test_get_job_for_user_or_404_returns_job
test_get_job_for_user_or_404_raises_for_invalid_user = _TopLevelFunctionSurface.test_get_job_for_user_or_404_raises_for_invalid_user
test_schedule_commit_adds_background_task = _TopLevelFunctionSurface.test_schedule_commit_adds_background_task
test_commit_job_task_processes_valid_rows_and_marks_completed = _TopLevelFunctionSurface.test_commit_job_task_processes_valid_rows_and_marks_completed
test_commit_job_task_accepts_summary_dict_with_produtos = _TopLevelFunctionSurface.test_commit_job_task_accepts_summary_dict_with_produtos










