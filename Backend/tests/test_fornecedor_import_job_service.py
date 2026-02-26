from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_import_job_service import (
    FornecedorImportJobService,
)


class _CrudFornecedorImportJobsStub:
    def __init__(self, job=None):
        self.job = job
        self.updated_status = None

    def get_import_job(self, db, job_id):
        _ = db
        if self.job and self.job.id == job_id:
            return self.job
        return None

    def update_job_status(self, db, job, status):
        _ = db
        job.status = status
        self.updated_status = status
        return job


class _CrudProdutosStub:
    def __init__(self):
        self.calls = []

    def get_or_create_produto(self, db, produto_schema, user_id):
        self.calls.append((db, produto_schema.payload, user_id))
        return SimpleNamespace(id=len(self.calls))


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


def _build_service(*, job):
    crud_jobs = _CrudFornecedorImportJobsStub(job=job)
    crud_produtos = _CrudProdutosStub()
    service = FornecedorImportJobService(
        crud_fornecedor_import_jobs=crud_jobs,
        crud_produtos=crud_produtos,
        produto_create_schema=_ProdutoCreateSchemaStub,
    )
    return service, crud_jobs, crud_produtos


def test_get_job_for_user_or_404_returns_job():
    job = SimpleNamespace(id=5, user_id=10, result_summary=[])
    service, _, _ = _build_service(job=job)

    found = service.get_job_for_user_or_404(db=object(), job_id=5, user_id=10)

    assert found is job


def test_get_job_for_user_or_404_raises_for_invalid_user():
    job = SimpleNamespace(id=5, user_id=10, result_summary=[])
    service, _, _ = _build_service(job=job)

    with pytest.raises(HTTPException) as exc:
        service.get_job_for_user_or_404(db=object(), job_id=5, user_id=99)

    assert exc.value.status_code == 404


def test_schedule_commit_adds_background_task():
    job = SimpleNamespace(id=5, user_id=10, result_summary=[])
    service, _, _ = _build_service(job=job)
    background = _BackgroundTasksStub()
    db = _DbSessionStub()

    service.schedule_commit(
        background_tasks=background,
        db=db,
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
    service, crud_jobs, crud_produtos = _build_service(job=job)

    db_instance = _DbSessionStub()

    def _factory():
        return db_instance

    service.commit_job_task(
        db_session_factory=_factory,
        job_id=5,
        user_id=10,
    )

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
    service, crud_jobs, crud_produtos = _build_service(job=job)

    db_instance = _DbSessionStub()

    service.commit_job_task(
        db_session_factory=lambda: db_instance,
        job_id=6,
        user_id=10,
    )

    assert len(crud_produtos.calls) == 2
    assert crud_jobs.updated_status == "COMPLETED"
