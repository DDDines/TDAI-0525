"""Additional detail tests for supplier import job service."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.services.fornecedor_import_job_service import (
    FornecedorImportJobService,
)


class _ImportJobRepoStub:
    """Simple import-job repository stub."""

    def __init__(self, job=None):
        self.job = job
        self.updated = None

    def get_import_job(self, job_id):
        if self.job and self.job.id == job_id:
            return self.job
        return None

    def update_job_status(self, job, status):
        self.updated = status
        job.status = status


class _ProdutoRepoStub:
    """Simple product repository stub."""

    def __init__(self):
        self.calls = []

    def get_or_create_produto(self, *, produto, user_id):
        self.calls.append((produto.payload, user_id))


class _SchemaStub:
    """Schema stub that requires ``nome_base``."""

    def __init__(self, **payload):
        if not payload.get("nome_base"):
            raise ValueError("nome_base obrigatorio")
        self.payload = payload


class _SessionStub:
    """Session stub exposing only ``close``."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _SessionProviderStub:
    """Session provider stub."""

    def __init__(self, session):
        self._session = session

    def open_session(self):
        return self._session


def _build_service(*, job=None, session_provider=None):
    """Build service and exposed repos for assertions."""
    job_repo = _ImportJobRepoStub(job=job)
    produto_repo = _ProdutoRepoStub()
    service = FornecedorImportJobService(
        session_provider=session_provider,
        import_job_repository_factory=lambda _session: job_repo,
        produto_repository_factory=lambda _session: produto_repo,
        produto_create_schema=_SchemaStub,
    )
    return service, job_repo, produto_repo


def test_get_job_for_user_or_404_requires_session_provider():
    """Cover the explicit missing-session-provider guard."""
    service, _, _ = _build_service(job=None, session_provider=None)
    with pytest.raises(ValueError):
        service.get_job_for_user_or_404(job_id=1, user_id=1)


def test_build_review_payload_defaults_to_empty_dict():
    """Cover the empty review-payload branch."""
    service, _, _ = _build_service(job=None, session_provider=SimpleNamespace(open_session=lambda: _SessionStub()))
    assert service.build_review_payload(job=SimpleNamespace(result_summary=None)) == {}


def test_commit_job_task_requires_session_provider_and_ignores_missing_job():
    """Cover missing-session-provider and missing-job commit branches."""
    service, _, _ = _build_service(job=None, session_provider=None)
    with pytest.raises(ValueError):
        service.commit_job_task(job_id=1, user_id=1)

    session = _SessionStub()
    service, job_repo, produto_repo = _build_service(
        job=None,
        session_provider=_SessionProviderStub(session),
    )
    service.commit_job_task(job_id=2, user_id=3)
    assert job_repo.updated is None
    assert produto_repo.calls == []
    assert session.closed is True


def test_commit_job_task_accepts_itens_summary_and_skips_invalid_rows():
    """Cover ``itens`` payloads and schema-failure skips during commit."""
    job = SimpleNamespace(
        id=7,
        user_id=10,
        status="REVIEW",
        result_summary={
            "itens": [
                {"nome_base": "Produto X", "sku_original": "SKU-X"},
                {"sku_original": "sem nome"},
                "ignorar",
            ]
        },
    )
    session = _SessionStub()
    service, job_repo, produto_repo = _build_service(
        job=job,
        session_provider=_SessionProviderStub(session),
    )
    service.commit_job_task(job_id=7, user_id=55)
    assert produto_repo.calls == [({"nome_base": "Produto X", "sku_original": "SKU-X"}, 55)]
    assert job_repo.updated == "COMPLETED"
    assert session.closed is True


def test_iter_summary_rows_covers_non_dict_and_multi_item_paths():
    """Cover the remaining summary iterator branches explicitly."""
    service, _, _ = _build_service(
        job=None,
        session_provider=_SessionProviderStub(_SessionStub()),
    )

    assert list(service._iter_summary_rows("ignorar")) == []
    assert list(
        service._iter_summary_rows(
            {"produtos": [{"nome_base": "A"}, "ignorar", {"nome_base": "B"}]}
        )
    ) == [{"nome_base": "A"}, {"nome_base": "B"}]
    assert list(service._iter_summary_rows({"produtos": "invalido", "itens": "x"})) == []
