"""Extra coverage for small adapters, repositories, previews and router details."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

import Backend.application.services.fornecedor_preview_service as fornecedor_preview_module
import Backend.routers.web_enrichment as web_enrichment_module
from Backend.application.services.catalog_import_diagnostics_service import (
    CatalogImportDiagnosticsService,
)
from Backend.application.services.file_processing.orchestrator_service import (
    FileProcessingOrchestratorService,
)
from Backend.application.services.fornecedor_preview_service import FornecedorPreviewService
from Backend.application.services.web_enrichment_start_service import (
    WebEnrichmentStartService,
)
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)
from Backend.infrastructure.adapters.file_processing_adapter import (
    FileProcessingServiceAdapter,
)
from Backend.infrastructure.adapters.limit_adapter import LimitServiceAdapter
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository


class _FakeAsyncRuntime:
    def __init__(self):
        self.calls = []

    async def save_uploaded_catalog(self, **kwargs):
        self.calls.append(("save_uploaded_catalog", kwargs))
        return {"stored": True}

    def delete_catalog_file(self, **kwargs):
        self.calls.append(("delete_catalog_file", kwargs))

    def get_file_path_by_id(self, **kwargs):
        self.calls.append(("get_file_path_by_id", kwargs))
        return "/tmp/catalog.pdf"

    async def processar_arquivo_excel(self, **kwargs):
        self.calls.append(("processar_arquivo_excel", kwargs))
        return [{"tipo": "excel"}]

    async def processar_arquivo_csv(self, **kwargs):
        self.calls.append(("processar_arquivo_csv", kwargs))
        return [{"tipo": "csv"}]

    async def processar_arquivo_pdf(self, **kwargs):
        self.calls.append(("processar_arquivo_pdf", kwargs))
        return [{"tipo": "pdf"}]

    async def preview_arquivo_excel(self, **kwargs):
        self.calls.append(("preview_arquivo_excel", kwargs))
        return {"rows": 1}

    async def preview_arquivo_csv(self, **kwargs):
        self.calls.append(("preview_arquivo_csv", kwargs))
        return {"rows": 2}

    async def preview_arquivo_pdf(self, **kwargs):
        self.calls.append(("preview_arquivo_pdf", kwargs))
        return {"pages": 1}

    async def gerar_preview(self, **kwargs):
        self.calls.append(("gerar_preview", kwargs))
        return {"preview": True}

    async def pdf_bytes_to_images(self, **kwargs):
        self.calls.append(("pdf_bytes_to_images", kwargs))
        return ["img://1"]

    def pdf_pages_to_images(self, **kwargs):
        self.calls.append(("pdf_pages_to_images", kwargs))
        return {"pages": []}

    async def extrair_pagina_pdf(self, **kwargs):
        self.calls.append(("extrair_pagina_pdf", kwargs))
        return {"page": kwargs["page_number"]}

    def generate_pdf_page_images(self, **kwargs):
        self.calls.append(("generate_pdf_page_images", kwargs))
        return ["img://1", "img://2"]

    def extract_pdf_region_image(self, **kwargs):
        self.calls.append(("extract_pdf_region_image", kwargs))
        return b"png"

    def parse_annotation_to_dataframe(self, **kwargs):
        self.calls.append(("parse_annotation_to_dataframe", kwargs))
        return "df"

    def extract_data_from_pdf_region(self, **kwargs):
        self.calls.append(("extract_data_from_pdf_region", kwargs))
        return "region-df"

    async def process_pdf_job(self, **kwargs):
        self.calls.append(("process_pdf_job", kwargs))

    def extract_data_from_single_page(self, **kwargs):
        self.calls.append(("extract_data_from_single_page", kwargs))
        return {"page": kwargs["page_number"]}

    def processar_linha_padronizada(self, **kwargs):
        self.calls.append(("processar_linha_padronizada", kwargs))
        return {"nome_base": "linha"}


class _LimitRuntime:
    def __init__(self):
        self.calls = []

    def verificar_limite_uso(self, **kwargs):
        self.calls.append(("verificar_limite_uso", kwargs))
        return 7

    async def verificar_creditos_disponiveis_geracao_ia(self, **kwargs):
        self.calls.append(("verificar_creditos_disponiveis_geracao_ia", kwargs))
        return True

    async def verificar_e_consumir_creditos_geracao_ia(self, **kwargs):
        self.calls.append(("verificar_e_consumir_creditos_geracao_ia", kwargs))
        return True


class _HistoricoQuery:
    def __init__(self, scalar_value=0):
        self.filters = []
        self.scalar_value = scalar_value
        self.offset_value = None
        self.limit_value = None

    def filter(self, condition):
        self.filters.append(condition)
        return self

    def order_by(self, *_args):
        return self

    def offset(self, value):
        self.offset_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        return ["registro"]

    def scalar(self):
        return self.scalar_value


class _HistoricoDb:
    def __init__(self):
        self.queries = []
        self.added = []
        self.commits = 0
        self.refreshed = []

    def query(self, *_args):
        query = _HistoricoQuery()
        self.queries.append(query)
        return query

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


class _LoggerStub:
    def __init__(self):
        self.messages = []

    def warning(self, message, *args):
        self.messages.append((message, args))


class _SanitizationStub:
    @staticmethod
    def extract_import_error_reason(item):
        return item.get("reason", "sem-motivo")


class _DataFrameStub:
    def __init__(self, *, empty, columns=None, rows=None):
        self.empty = empty
        self._columns = columns or []
        self._rows = rows or []

    @property
    def columns(self):
        return SimpleNamespace(astype=lambda _type: SimpleNamespace(tolist=lambda: self._columns))

    def head(self, _limit):
        return self

    def to_dict(self, orient):
        assert orient == "records"
        return self._rows


class _FilePreviewStub:
    def __init__(self):
        self._file_path = "/tmp/catalog.pdf"
        self._df = None
        self.bulk_calls = []

    def generate_pdf_page_images(self, file_path, file_id):
        return [f"img://{file_id}", file_path]

    def pdf_pages_to_images(self, **kwargs):
        self.bulk_calls.append(("pdf_pages_to_images", kwargs))
        return {"pages": [{"page_number": 1}]}

    def get_file_path_by_id(self, *_args, **_kwargs):
        return self._file_path

    def extract_pdf_region_image(self, **kwargs):
        self.bulk_calls.append(("extract_pdf_region_image", kwargs))
        return b"png"

    def parse_annotation_to_dataframe(self, _annotation):
        return self._df

    def extract_data_from_pdf_region(self, **kwargs):
        self.bulk_calls.append(("extract_data_from_pdf_region", kwargs))


class _WebExtractorStub:
    def extract_text_from_image_region(self, _image_bytes):
        return "annotation"


class _CatalogRepoStub:
    def __init__(self):
        self._db = "db-session"


class _BackgroundTasksStub:
    def __init__(self):
        self.calls = []

    def add_task(self, fn, **kwargs):
        self.calls.append((fn, kwargs))


class _PdfStub:
    def __init__(self, pages_count):
        self.pages = [object() for _ in range(pages_count)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        _ = (exc_type, exc, tb)
        return False


@pytest.mark.asyncio
async def test_file_processing_adapter_and_orchestrator_delegate_remaining_methods():
    runtime = _FakeAsyncRuntime()
    adapter = FileProcessingServiceAdapter(runtime=runtime)
    orchestrator = FileProcessingOrchestratorService(runtime)

    assert await adapter.save_uploaded_catalog(file="file", fornecedor_id=3) == {"stored": True}
    assert adapter.delete_catalog_file("catalog.pdf") is None
    assert adapter.get_file_path_by_id("db", 1) == "/tmp/catalog.pdf"
    assert await adapter.processar_arquivo_excel(b"x", {"sku": "sku"}, "Plan1", 7) == [{"tipo": "excel"}]
    assert await adapter.processar_arquivo_csv(b"x", {"sku": "sku"}, 7) == [{"tipo": "csv"}]
    assert await adapter.processar_arquivo_pdf(b"%PDF", {"sku": "sku"}, True, 7, [1], [1.0], "ocr") == [{"tipo": "pdf"}]
    assert await adapter.preview_arquivo_excel(b"x") == {"rows": 1}
    assert await adapter.preview_arquivo_csv(b"x") == {"rows": 2}
    assert await adapter.preview_arquivo_pdf(b"%PDF", ".pdf") == {"pages": 1}
    assert await adapter.gerar_preview(b"%PDF", ".pdf") == {"preview": True}
    assert await adapter.pdf_bytes_to_images(b"%PDF") == ["img://1"]
    assert adapter.pdf_pages_to_images("db", "file", 1, 2, 0, 10) == {"pages": []}
    assert await adapter.extrair_pagina_pdf(b"%PDF", 2, [1.0]) == {"page": 2}
    assert adapter.generate_pdf_page_images("file.pdf", "id") == ["img://1", "img://2"]
    assert adapter.extract_pdf_region_image("file.pdf", 2, [1.0], 300) == b"png"
    assert adapter.parse_annotation_to_dataframe("annotation", 7) == "df"
    assert adapter.extract_data_from_pdf_region("file.pdf", 2, [1.0]) == "region-df"
    assert await adapter.process_pdf_job(10, "file.pdf", 2, {"sku": "sku"}) is None
    assert adapter.extract_data_from_single_page("file.pdf", 2) == {"page": 2}
    assert adapter.processar_linha_padronizada({"sku": "1"}, {"sku": "sku"}) == {"nome_base": "linha"}

    assert await orchestrator.save_uploaded_catalog(file="file", fornecedor_id=4) == {"stored": True}
    assert orchestrator.delete_catalog_file("catalog.pdf") is None
    assert orchestrator.get_file_path_by_id("db", 2) == "/tmp/catalog.pdf"
    assert await orchestrator.processar_arquivo_excel(b"x", {"sku": "sku"}, "Plan1", 8) == [{"tipo": "excel"}]
    assert await orchestrator.processar_arquivo_csv(b"x", {"sku": "sku"}, 8) == [{"tipo": "csv"}]
    assert await orchestrator.processar_arquivo_pdf(b"%PDF", {"sku": "sku"}, True, 8, [1], [1.0], "ocr") == [{"tipo": "pdf"}]
    assert await orchestrator.preview_arquivo_excel(b"x") == {"rows": 1}
    assert await orchestrator.preview_arquivo_csv(b"x") == {"rows": 2}
    assert await orchestrator.preview_arquivo_pdf(b"%PDF", ".pdf") == {"pages": 1}
    assert await orchestrator.gerar_preview(b"%PDF", ".pdf") == {"preview": True}
    assert await orchestrator.pdf_bytes_to_images(b"%PDF") == ["img://1"]
    assert orchestrator.pdf_pages_to_images("db", "file", 1, 2, 0, 10) == {"pages": []}
    assert await orchestrator.extrair_pagina_pdf(b"%PDF", 3, [2.0]) == {"page": 3}
    assert orchestrator.generate_pdf_page_images("file.pdf", "id") == ["img://1", "img://2"]
    assert orchestrator.extract_pdf_region_image("file.pdf", 1, [2.0], 300) == b"png"
    assert orchestrator.parse_annotation_to_dataframe("annotation", 9) == "df"
    assert orchestrator.extract_data_from_pdf_region("file.pdf", 4, [2.0]) == "region-df"
    assert await orchestrator.process_pdf_job(11, "file.pdf", 1, {"sku": "sku"}) is None
    assert orchestrator.extract_data_from_single_page("file.pdf", 5) == {"page": 5}
    assert orchestrator.processar_linha_padronizada({"sku": "1"}, {"sku": "sku"}) == {"nome_base": "linha"}


@pytest.mark.asyncio
async def test_limit_adapter_and_web_enrichment_use_case_details():
    runtime = _LimitRuntime()
    adapter = LimitServiceAdapter(runtime=runtime)

    assert adapter.verificar_limite_uso("db", SimpleNamespace(id=1), "titulo") == 7
    assert await adapter.verificar_creditos_disponiveis_geracao_ia("db", 5, 2) is True
    assert await adapter.verificar_e_consumir_creditos_geracao_ia("db", 5, 3) is True

    calls = []

    async def _processor(**kwargs):
        calls.append(kwargs)
        return kwargs

    use_case = WebEnrichmentProcessingUseCase(_processor)
    assert await use_case.execute(produto_id=3, user_id=4, termos_busca_override="  termo  ") == {
        "produto_id": 3,
        "user_id": 4,
        "termos_busca_override": "termo",
    }
    with pytest.raises(ValueError):
        await use_case.execute(produto_id=0, user_id=4)


def test_historico_repository_filters_create_and_count_defaults():
    db = _HistoricoDb()
    repo = HistoricoRepository(db)
    created = repo.create_registro_historico(
        SimpleNamespace(model_dump=lambda exclude_unset=True: {"user_id": 1, "entidade": "produto"})
    )
    assert created.user_id == 1
    assert db.commits == 1

    registros = repo.get_registros_historico(
        user_id=7,
        skip=3,
        limit=9,
        entidade="produto",
        acao="CRIACAO",
    )
    assert registros == ["registro"]
    assert db.queries[0].offset_value == 3
    assert db.queries[0].limit_value == 9
    assert len(db.queries[0].filters) == 3

    db.queries.clear()
    db.query = lambda *_args: _HistoricoQuery(scalar_value=None)
    assert repo.count_registros_historico(user_id=7, entidade="produto", acao="CRIACAO") == 0


def test_catalog_import_diagnostics_error_path_and_relative_resolution(tmp_path, monkeypatch):
    logger = _LoggerStub()
    service = CatalogImportDiagnosticsService(
        catalog_log_dir=tmp_path / "logs",
        logger=logger,
        sanitization_service=_SanitizationStub(),
    )
    assert service.resolve_storage_path("uploads/catalogs/file.pdf").parts[-3:] == (
        "uploads",
        "catalogs",
        "file.pdf",
    )

    class _BrokenPath:
        def write_text(self, *_args, **_kwargs):
            raise RuntimeError("disk-full")

    monkeypatch.setattr(Path, "write_text", _BrokenPath.write_text, raising=False)
    assert (
        service.write_catalog_import_report(
            file_id=10,
            status="FAILED",
            created_count=0,
            updated_count=0,
            errors=[{"reason": "erro"}],
        )
        is None
    )
    assert logger.messages


@pytest.mark.asyncio
async def test_fornecedor_preview_start_service_and_web_enrichment_router_details(monkeypatch):
    file_processing = _FilePreviewStub()
    service = FornecedorPreviewService(
        file_processing_service=file_processing,
        web_data_extractor_service=_WebExtractorStub(),
        catalog_file_repository=_CatalogRepoStub(),
    )

    file_processing._file_path = None
    with pytest.raises(HTTPException) as exc_info:
        service.preview_catalog_from_region(file_id=1, page_number=2, region=[1, 2, 3, 4])
    assert exc_info.value.status_code == 404

    file_processing._file_path = None
    with pytest.raises(HTTPException) as exc_info:
        service.extract_data_from_pdf_bulk(
            background_tasks=_BackgroundTasksStub(),
            file_id=1,
            region=[1, 2, 3, 4],
            pages=[1],
            all_pages=False,
        )
    assert exc_info.value.status_code == 404

    file_processing._file_path = "/tmp/catalog.pdf"
    tasks = _BackgroundTasksStub()
    monkeypatch.setattr(fornecedor_preview_module.pdfplumber, "open", lambda _path: _PdfStub(3))
    payload = service.extract_data_from_pdf_bulk(
        background_tasks=tasks,
        file_id=1,
        region=[1, 2, 3, 4],
        pages=[0, 2, 5],
        all_pages=False,
    )
    assert payload == {"detail": "Batch processing started", "total_pages": 3}
    assert len(tasks.calls) == 1
    assert tasks.calls[0][1]["page_number"] == 2

    product_repository = SimpleNamespace(
        get_produto=lambda **_kwargs: SimpleNamespace(user_id=1, status_enriquecimento_web="LIVRE")
    )
    models_stub = SimpleNamespace(StatusEnriquecimentoEnum=SimpleNamespace(EM_PROGRESSO="EM_PROGRESSO"))
    start_service = WebEnrichmentStartService(
        models=models_stub,
        product_repository=product_repository,
        dispatcher_cls=SimpleNamespace(dispatch_background=lambda *_args, **_kwargs: None),
        orchestrator_cls=lambda **kwargs: SimpleNamespace(select_start_plan=lambda command: command),
    )
    start_service._mark_pending_status(produto_id=9)

    update_only_repo = SimpleNamespace(
        get_produto=lambda **_kwargs: SimpleNamespace(user_id=1, status_enriquecimento_web="LIVRE"),
        set_web_enrichment_status=None,
    )
    start_service = WebEnrichmentStartService(
        models=SimpleNamespace(StatusEnriquecimentoEnum=SimpleNamespace(EM_PROGRESSO="EM_PROGRESSO", PENDENTE="PENDENTE")),
        product_repository=update_only_repo,
        dispatcher_cls=SimpleNamespace(dispatch_background=lambda *_args, **_kwargs: None),
        orchestrator_cls=lambda **kwargs: SimpleNamespace(select_start_plan=lambda command: command),
    )
    start_service._mark_pending_status(produto_id=10)

    session = SimpleNamespace(get_bind=lambda: "engine")
    calls = []
    monkeypatch.setattr(
        web_enrichment_module.ServiceContainerDependencySupport,
        "build_background_session_provider_from_session",
        lambda provided_session: calls.append(("session_provider", provided_session)) or "provider",
    )
    monkeypatch.setattr(
        web_enrichment_module,
        "WebDataExtractorOrchestratorService",
        lambda adapter: ("extractor", adapter),
    )
    monkeypatch.setattr(
        web_enrichment_module,
        "WebDataExtractorServiceAdapter",
        lambda: "adapter",
    )
    monkeypatch.setattr(
        web_enrichment_module,
        "WebEnrichmentTaskRunner",
        lambda **kwargs: calls.append(("runner", kwargs)) or SimpleNamespace(execute=lambda **_kw: None),
    )
    monkeypatch.setattr(
        web_enrichment_module,
        "ProductRepository",
        lambda provided_session: ("product-repo", provided_session),
    )
    monkeypatch.setattr(
        web_enrichment_module,
        "WebEnrichmentStartService",
        lambda **kwargs: calls.append(("start-service", kwargs)) or SimpleNamespace(
            validate_start_preconditions=lambda **_kw: None,
            dispatch_start=lambda **_kw: None,
        ),
    )
    web_enrichment_module.WebEnrichmentRequestService(session=session)
    assert calls[0] == ("session_provider", session)

    request_service = SimpleNamespace(
        iniciar_enriquecimento_produto_web=lambda **kwargs: {"msg": f"ok:{kwargs['produto_id']}"}
    )
    endpoint_result = await web_enrichment_module.iniciar_enriquecimento_produto_web_endpoint(
        produto_id=17,
        background_tasks=BackgroundTasks(),
        current_user=SimpleNamespace(id=3, is_superuser=False),
        termos_busca_override="termo",
        request_service=request_service,
    )
    assert endpoint_result == {"msg": "ok:17"}
