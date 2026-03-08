"""Additional detail tests for catalog import task workflow/service."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import Backend.application.services.catalog_import_task_service as task_module
from Backend.application.services.catalog_import_task_service import (
    CatalogImportTaskService,
    CatalogImportTaskWorkflow,
)


class _LoggerStub:
    """Tiny logger stub collecting calls."""

    def __init__(self):
        self.calls = []

    def info(self, *args, **kwargs):
        self.calls.append(("info", args, kwargs))

    def error(self, *args, **kwargs):
        self.calls.append(("error", args, kwargs))

    def warning(self, *args, **kwargs):
        self.calls.append(("warning", args, kwargs))

    def exception(self, *args, **kwargs):
        self.calls.append(("exception", args, kwargs))


class _SessionStub:
    """Minimal DB session stub."""

    def __init__(self):
        self.closed = False
        self.committed = False

    def close(self):
        self.closed = True

    def commit(self):
        self.committed = True


class _SessionProvider:
    """Open-session stub."""

    def __init__(self, session):
        self._session = session

    def open_session(self):
        return self._session


class _PathStub:
    """Filesystem path stub for resolve-file tests."""

    def __init__(self, *, exists, suffix=".pdf", content=b"content"):
        self._exists = exists
        self.suffix = suffix
        self._content = content

    def exists(self):
        return self._exists

    def read_bytes(self):
        return self._content


class _IssueTrackerStub:
    """Issue tracker stub."""

    def __init__(self):
        self.errors = []
        self.ignored_non_critical = []
        self.quarantine = []

    def add_issue(self, item):
        self.errors.append(item)

    def add_quarantine_issue(self, item):
        self.quarantine.append(item)


class _QualityScoresStub:
    """Quality accumulator stub."""

    def __init__(self):
        self.accepted = []
        self.quarantine = []

    def add_quarantine(self, value):
        self.quarantine.append(value)

    def add_accepted(self, value):
        self.accepted.append(value)


class _FileStateStub:
    """File state service stub."""

    def __init__(self):
        self.calls = []

    def mark_processing(self, **kwargs):
        self.calls.append(("mark_processing", kwargs))

    def mark_file_missing(self, **kwargs):
        self.calls.append(("mark_file_missing", kwargs))

    def initialize_pages(self, **kwargs):
        self.calls.append(("initialize_pages", kwargs))

    def increment_page(self, **kwargs):
        self.calls.append(("increment_page", kwargs))

    def mark_final(self, **kwargs):
        self.calls.append(("mark_final", kwargs))

    def mark_failure_with_exception(self, **kwargs):
        self.calls.append(("mark_failure_with_exception", kwargs))


class _SchemaCreateStub:
    """ProdutoCreate stub that stores payload and can fail without name."""

    def __init__(self, **kwargs):
        if kwargs.get("nome_base") == "quebrar":
            raise RuntimeError("schema invalido")
        self.payload = kwargs


def _build_workflow(*, session_provider=None):
    """Build a workflow with simple injectable collaborators."""
    logger = _LoggerStub()
    catalog_logger = _LoggerStub()
    workflow = CatalogImportTaskWorkflow(
        session_provider=session_provider or _SessionProvider(_SessionStub()),
        logger=logger,
        catalog_logger=catalog_logger,
        models=SimpleNamespace(),
        schemas=SimpleNamespace(ProdutoCreate=_SchemaCreateStub),
        product_repository_factory=lambda _session: SimpleNamespace(),
        catalog_file_repository_factory=lambda _session: SimpleNamespace(),
        file_processing_service=SimpleNamespace(),
        validator_crew=SimpleNamespace(run_validation_crew=lambda prod: prod),
        settings=SimpleNamespace(UPLOAD_DIRECTORY="uploads"),
        Path=Path,
        time=SimpleNamespace(perf_counter=lambda: 1.0),
        Counter=dict,
        resolve_storage_path=lambda path: path,
        normalize_import_issue_item=lambda item: item,
        extract_import_error_reason=lambda item: "erro",
        is_non_critical_import_reason=lambda reason: False,
        normalizar_dados_validados=lambda validated, original: validated,
        sanitize_produto_extraido=lambda prod: prod,
        classificar_qualidade_linha_produto=lambda prod: {"decision": "accept", "score": 100, "reason": None},
        write_catalog_import_report=lambda **kwargs: None,
        normalize_import_text=lambda text: text,
    )
    workflow.issue_tracker = _IssueTrackerStub()
    workflow.quality_scores = _QualityScoresStub()
    workflow.file_state_service = _FileStateStub()
    workflow.audit_writer = SimpleNamespace(register_creation=lambda **kwargs: None)
    workflow.catalog_file_repo_runtime = SimpleNamespace(
        get_catalog_file_for_user=lambda **kwargs: None,
        get_catalog_file=lambda **kwargs: None,
    )
    workflow.product_repo_runtime = SimpleNamespace(
        create_produtos_bulk=lambda **kwargs: ([], [], [])
    )
    return workflow


def test_load_catalog_file_returns_false_when_file_is_missing():
    """Cover the explicit missing-catalog-file branch."""
    workflow = _build_workflow()
    workflow.file_id = 10
    workflow.user_id = 20
    assert workflow._load_catalog_file() is False
    assert any(level == "error" for level, *_ in workflow.logger.calls)


def test_resolve_file_marks_missing_storage_and_returns_nones():
    """Cover storage-missing resolution branch."""
    workflow = _build_workflow()
    workflow.file_id = 10
    workflow.catalog_file = SimpleNamespace(stored_filename="catalogo.pdf")
    workflow.file_state_service = _FileStateStub()
    workflow.resolve_storage_path = lambda _path: _PathStub(exists=False)
    file_path, content, ext = workflow._resolve_file()
    assert (file_path, content, ext) == (None, None, None)
    assert workflow.file_state_service.calls[0][0] == "mark_file_missing"


def test_process_quality_and_schema_handles_issue_quarantine_and_schema_error():
    """Cover early-return, quarantine, and schema-conversion error branches."""
    workflow = _build_workflow()
    produtos_create = []

    workflow._process_quality_and_schema(
        prod={"motivo_descarte": "ruido"},
        conversion_error_prefix="erro",
        produtos_create=produtos_create,
    )
    assert workflow.issue_tracker.errors[0]["motivo_descarte"] == "ruido"

    workflow.classificar_qualidade_linha_produto = (
        lambda prod: {"decision": "quarantine", "score": 22, "reason": "suspeito"}
    )
    workflow.quality_filter_enabled = True
    workflow._process_quality_and_schema(
        prod={"nome_base": "Produto A"},
        conversion_error_prefix="erro",
        produtos_create=produtos_create,
    )
    assert workflow.quality_scores.quarantine == [22]
    assert workflow.issue_tracker.quarantine[0]["classificacao"] == "quarentena"

    workflow.classificar_qualidade_linha_produto = (
        lambda prod: {"decision": "accept", "score": 100, "reason": None}
    )
    workflow._process_quality_and_schema(
        prod={"nome_base": "quebrar"},
        conversion_error_prefix="Erro ao converter",
        produtos_create=produtos_create,
    )
    assert any("Erro ao converter" in item["motivo_descarte"] for item in workflow.issue_tracker.errors)


def test_flush_produtos_handles_empty_batches_and_duplicate_errors():
    """Cover no-op flush and duplicate-error registration paths."""
    workflow = _build_workflow()
    workflow.created = []
    workflow.updated = []
    created, updated = workflow._flush_produtos(produtos_create=[])
    assert created == []
    assert updated == []

    audit_calls = []
    workflow.audit_writer = SimpleNamespace(register_creation=lambda **kwargs: audit_calls.append(kwargs))
    workflow.product_repo_runtime = SimpleNamespace(
        create_produtos_bulk=lambda **kwargs: (
            [SimpleNamespace(id=1)],
            [SimpleNamespace(id=2)],
            [{"erro_processamento": "duplicado"}],
        )
    )
    workflow.db = _SessionStub()
    workflow.user_id = 7
    created, updated = workflow._flush_produtos(produtos_create=[SimpleNamespace()])
    assert [item.id for item in created] == [1]
    assert [item.id for item in updated] == [2]
    assert workflow.issue_tracker.errors[-1]["erro_processamento"] == "duplicado"
    assert audit_calls[0]["user_id"] == 7


@pytest.mark.asyncio
async def test_process_tabular_handles_excel_and_unsupported_extensions():
    """Cover excel-processing branch and unsupported-extension failure branch."""
    workflow = _build_workflow()
    workflow.catalog_file = SimpleNamespace(total_pages=1, pages_processed=0)
    workflow.file_state_service = _FileStateStub()
    processed = []
    workflow.file_processing_service = SimpleNamespace(
        processar_arquivo_excel=lambda *args, **kwargs: asyncio.sleep(0, result=[{"nome_base": "Produto A"}]),
        processar_arquivo_csv=lambda *args, **kwargs: asyncio.sleep(0, result=[]),
    )
    workflow._process_quality_and_schema = lambda **kwargs: processed.append(kwargs["prod"])
    workflow._flush_produtos = lambda **kwargs: ([], [])
    workflow.db = _SessionStub()
    workflow.mapping = {}
    workflow.product_type_id = 3
    ok = await workflow._process_tabular(ext=".xlsx", content=b"x")
    assert ok is True
    assert processed == [{"nome_base": "Produto A"}]
    assert workflow.db.committed is True

    workflow.file_state_service = _FileStateStub()
    failed = await workflow._process_tabular(ext=".txt", content=b"x")
    assert failed is False
    assert workflow.file_state_service.calls[-1][0] == "mark_final"


def test_handle_failure_skips_without_db_and_marks_catalog_when_present():
    """Cover failure handling with and without a live DB session."""
    workflow = _build_workflow()
    workflow.db = None
    workflow._handle_failure(RuntimeError("boom"))
    assert any(level == "exception" for level, *_ in workflow.logger.calls)

    workflow.db = _SessionStub()
    workflow.file_state_service = _FileStateStub()
    workflow.catalog_file_repo_runtime = SimpleNamespace(
        get_catalog_file=lambda **kwargs: SimpleNamespace(id=1)
    )
    workflow.file_id = 9
    workflow._handle_failure(RuntimeError("boom2"))
    assert workflow.file_state_service.calls[-1][0] == "mark_failure_with_exception"


@pytest.mark.asyncio
async def test_run_covers_guards_early_returns_and_failure_path():
    """Cover session-provider guard plus early returns/failure handling inside ``run``."""
    workflow = _build_workflow(session_provider=None)
    workflow._session_provider = None
    with pytest.raises(ValueError):
        await workflow.run(file_id=1, user_id=2, product_type_id=None, fornecedor_id=3)

    session_missing_load = _SessionStub()
    workflow_missing_load = _build_workflow(session_provider=_SessionProvider(session_missing_load))
    workflow_missing_load._load_catalog_file = lambda: False
    await workflow_missing_load.run(file_id=1, user_id=2, product_type_id=None, fornecedor_id=3)
    assert session_missing_load.closed is True

    session_missing_file = _SessionStub()
    workflow_missing_file = _build_workflow(session_provider=_SessionProvider(session_missing_file))
    workflow_missing_file._load_catalog_file = lambda: True
    workflow_missing_file._resolve_file = lambda: (None, None, None)
    await workflow_missing_file.run(file_id=1, user_id=2, product_type_id=None, fornecedor_id=3)
    assert session_missing_file.closed is True

    session_tabular_false = _SessionStub()
    workflow_tabular_false = _build_workflow(session_provider=_SessionProvider(session_tabular_false))
    workflow_tabular_false._load_catalog_file = lambda: True
    workflow_tabular_false._resolve_file = lambda: (_PathStub(exists=True, suffix=".csv"), b"x", ".csv")
    workflow_tabular_false._process_tabular = lambda **kwargs: asyncio.sleep(0, result=False)
    await workflow_tabular_false.run(file_id=1, user_id=2, product_type_id=None, fornecedor_id=3)
    assert session_tabular_false.closed is True

    session_failure = _SessionStub()
    workflow_failure = _build_workflow(session_provider=_SessionProvider(session_failure))
    workflow_failure._load_catalog_file = lambda: True
    workflow_failure._resolve_file = lambda: (_PathStub(exists=True, suffix=".pdf"), b"x", ".pdf")

    async def _boom(**kwargs):
        _ = kwargs
        raise RuntimeError("falhou")

    captured = []
    workflow_failure._process_pdf = _boom
    workflow_failure._handle_failure = lambda error: captured.append(str(error))
    await workflow_failure.run(file_id=1, user_id=2, product_type_id=None, fornecedor_id=3)
    assert captured == ["falhou"]
    assert session_failure.closed is True


@pytest.mark.asyncio
async def test_catalog_import_task_service_execute_forwards_arguments(monkeypatch):
    """Cover the thin service wrapper around workflow execution."""
    captured = {}

    class _WorkflowStub:
        def __init__(self, **kwargs):
            captured["deps"] = kwargs

        async def run(self, **kwargs):
            captured["run"] = kwargs

    monkeypatch.setattr(task_module, "CatalogImportTaskWorkflow", _WorkflowStub)
    service = CatalogImportTaskService(
        session_provider=_SessionProvider(_SessionStub()),
        logger=_LoggerStub(),
        catalog_logger=_LoggerStub(),
        models=SimpleNamespace(),
        schemas=SimpleNamespace(),
        product_repository_factory=lambda _session: None,
        catalog_file_repository_factory=lambda _session: None,
        file_processing_service=SimpleNamespace(),
        validator_crew=SimpleNamespace(),
        settings=SimpleNamespace(),
        Path=Path,
        time=SimpleNamespace(),
        Counter=dict,
        resolve_storage_path=lambda p: p,
        normalize_import_issue_item=lambda item: item,
        extract_import_error_reason=lambda item: "erro",
        is_non_critical_import_reason=lambda reason: False,
        normalizar_dados_validados=lambda validated, original: validated,
        sanitize_produto_extraido=lambda prod: prod,
        classificar_qualidade_linha_produto=lambda prod: {"decision": "accept", "score": 100},
        write_catalog_import_report=lambda **kwargs: None,
        normalize_import_text=lambda text: text,
    )
    await service.execute(
        file_id=10,
        user_id=20,
        product_type_id=30,
        fornecedor_id=40,
        mapping={"a": "b"},
        pages=[1, 2],
        region=[0.1, 0.2, 0.3, 0.4],
        extraction_mode="ia",
    )
    assert captured["run"] == {
        "file_id": 10,
        "user_id": 20,
        "product_type_id": 30,
        "fornecedor_id": 40,
        "mapping": {"a": "b"},
        "pages": [1, 2],
        "region": [0.1, 0.2, 0.3, 0.4],
        "extraction_mode": "ia",
    }
