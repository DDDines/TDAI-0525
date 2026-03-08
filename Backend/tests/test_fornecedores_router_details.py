"""Targeted coverage for fornecedores request/runtime delegates and endpoint wrappers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import schemas
from Backend.routers import fornecedores as fornecedores_module


def _fornecedor_create() -> schemas.FornecedorCreate:
    return schemas.FornecedorCreate(nome="Fornecedor Teste")


def _fornecedor_update() -> schemas.FornecedorUpdate:
    return schemas.FornecedorUpdate(nome="Fornecedor Atualizado")


class _Recorder:
    def __init__(self):
        self.calls = []

    def add(self, name, payload):
        self.calls.append((name, payload))


def test_fornecedores_dependencies_build_bundle_and_request_service(monkeypatch):
    class FakeBundle:
        pass

    class FakeGateway:
        def __init__(self, *, session):
            self.session = session

    monkeypatch.setattr(fornecedores_module, "_FornecedoresServiceBundle", FakeBundle)
    monkeypatch.setattr(fornecedores_module, "_FornecedoresServiceGateway", FakeGateway)

    bundle = fornecedores_module._FornecedoresDependencies._build_fornecedores_service_bundle()
    service = fornecedores_module._FornecedoresDependencies.get_fornecedores_request_service(session="db")

    assert isinstance(bundle, FakeBundle)
    assert isinstance(service, fornecedores_module.FornecedoresRequestService)
    assert service._runtime.session == "db"


def test_fornecedores_service_bundle_init_wires_collaborators(monkeypatch):
    recorder = _Recorder()
    session_provider = object()

    class FakeServiceContainer:
        def __init__(self):
            self.file_processing = "file-processing"
            self.web_data_extractor = "web-extractor"

    class FakeCatalogQualityService:
        def __init__(self):
            self.classify_product_row_quality = "quality-classifier"

    class FakeCatalogSanitizationService:
        def __init__(self, *, quality_service):
            recorder.add("CatalogImportSanitizationService", {"quality_service": quality_service})
            self.normalize_import_issue_item = "normalize-issue"
            self.extract_import_error_reason = "extract-reason"
            self.is_non_critical_import_reason = "is-non-critical"
            self.normalize_validated_data = "normalize-validated"
            self.sanitize_extracted_product = "sanitize-product"
            self.normalize_import_text = "normalize-text"

    class FakeCatalogDiagnosticsService:
        def __init__(self, **kwargs):
            recorder.add("CatalogImportDiagnosticsService", kwargs)
            self.resolve_storage_path = "resolve-path"
            self.write_catalog_import_report = "write-report"

    class FakeValidatorCrewService:
        def __init__(self, **kwargs):
            recorder.add("ValidatorCrewService", kwargs)

    class FakeCatalogImportTaskRunner:
        def __init__(self, **kwargs):
            recorder.add("CatalogImportTaskRunner", kwargs)

        def execute(self):
            return "executed"

    class FakeCatalogImportFinalizeService:
        def __init__(self, **kwargs):
            recorder.add("CatalogImportFinalizeService", kwargs)

    class FakeCatalogImportStartService:
        def __init__(self, **kwargs):
            recorder.add("CatalogImportStartService", kwargs)

    class FakeFornecedorCatalogProcessService:
        def __init__(self, **kwargs):
            recorder.add("FornecedorCatalogProcessService", kwargs)

    class FakeFornecedorImportJobService:
        def __init__(self, **kwargs):
            recorder.add("FornecedorImportJobService", kwargs)

    class FakeTaskWorkflow:
        def process_pdf_extraction_task(self):
            return "process-pdf-task"

    class FakeFornecedorImportTrackingService:
        def __init__(self, **kwargs):
            recorder.add("FornecedorImportTrackingService", kwargs)

    class FakeFornecedorPreviewService:
        def __init__(self, **kwargs):
            recorder.add("FornecedorPreviewService", kwargs)

    monkeypatch.setattr(fornecedores_module, "ServiceContainer", FakeServiceContainer)
    monkeypatch.setattr(fornecedores_module, "CatalogImportQualityService", FakeCatalogQualityService)
    monkeypatch.setattr(fornecedores_module, "CatalogImportSanitizationService", FakeCatalogSanitizationService)
    monkeypatch.setattr(fornecedores_module, "CatalogImportDiagnosticsService", FakeCatalogDiagnosticsService)
    monkeypatch.setattr(fornecedores_module, "ValidatorCrewService", FakeValidatorCrewService)
    monkeypatch.setattr(fornecedores_module, "CatalogImportTaskRunner", FakeCatalogImportTaskRunner)
    monkeypatch.setattr(fornecedores_module, "CatalogImportFinalizeService", FakeCatalogImportFinalizeService)
    monkeypatch.setattr(fornecedores_module, "CatalogImportStartService", FakeCatalogImportStartService)
    monkeypatch.setattr(fornecedores_module, "FornecedorCatalogProcessService", FakeFornecedorCatalogProcessService)
    monkeypatch.setattr(fornecedores_module, "FornecedorImportJobService", FakeFornecedorImportJobService)
    monkeypatch.setattr(fornecedores_module, "FornecedorImportTrackingService", FakeFornecedorImportTrackingService)
    monkeypatch.setattr(fornecedores_module, "FornecedorPreviewService", FakeFornecedorPreviewService)
    monkeypatch.setattr(fornecedores_module, "TaskWorkflow", FakeTaskWorkflow)

    bundle = fornecedores_module._FornecedoresServiceBundle(session_provider=session_provider)

    assert bundle.file_processing_service == "file-processing"
    assert bundle.web_data_extractor_service == "web-extractor"
    assert bundle._session_provider is session_provider
    assert any(name == "CatalogImportTaskRunner" for name, _payload in recorder.calls)
    assert any(name == "FornecedorPreviewService" for name, _payload in recorder.calls)


def test_fornecedores_gateway_init_wires_runtime_services(monkeypatch):
    recorder = _Recorder()
    fake_services = SimpleNamespace(
        catalog_import_diagnostics_service=SimpleNamespace(resolve_storage_path="resolve-path"),
        catalog_import_finalize_service="finalize-service",
        file_processing_service="file-processing",
        web_data_extractor_service="web-extractor",
        fornecedor_import_job_service="job-service",
    )

    monkeypatch.setattr(
        fornecedores_module.ServiceContainerDependencySupport,
        "build_background_session_provider_from_session",
        staticmethod(lambda session: ("provider", session)),
    )
    monkeypatch.setattr(
        fornecedores_module,
        "CatalogImportFileRepository",
        lambda session: recorder.add("CatalogImportFileRepository", {"session": session}) or "catalog-file-repo",
    )
    monkeypatch.setattr(
        fornecedores_module,
        "FornecedorRepository",
        lambda session: recorder.add("FornecedorRepository", {"session": session}) or "fornecedor-repo",
    )
    monkeypatch.setattr(
        fornecedores_module,
        "CatalogImportStartService",
        lambda **kwargs: recorder.add("CatalogImportStartService", kwargs) or "start-service",
    )
    monkeypatch.setattr(
        fornecedores_module,
        "FornecedorCatalogProcessService",
        lambda **kwargs: recorder.add("FornecedorCatalogProcessService", kwargs) or "catalog-process",
    )

    class FakeTaskWorkflow:
        def process_pdf_extraction_task(self):
            return "pdf-task"

    monkeypatch.setattr(fornecedores_module, "TaskWorkflow", FakeTaskWorkflow)
    monkeypatch.setattr(
        fornecedores_module,
        "FornecedorImportTrackingService",
        lambda **kwargs: recorder.add("FornecedorImportTrackingService", kwargs) or "tracking-service",
    )
    monkeypatch.setattr(
        fornecedores_module,
        "FornecedorPreviewService",
        lambda **kwargs: recorder.add("FornecedorPreviewService", kwargs) or "preview-service",
    )

    gateway = fornecedores_module._FornecedoresServiceGateway(session="db", services=fake_services)

    assert gateway._catalog_file_repo == "catalog-file-repo"
    assert gateway._fornecedor_repo == "fornecedor-repo"
    assert gateway._catalog_import_start_service == "start-service"
    assert gateway._fornecedor_catalog_process_service == "catalog-process"
    assert gateway._fornecedor_import_tracking_service == "tracking-service"
    assert gateway._fornecedor_preview_service == "preview-service"
    assert gateway._fornecedor_import_job_service == "job-service"


@pytest.mark.asyncio
async def test_fornecedores_gateway_covers_remaining_delegate_methods():
    management_calls = []
    preview_calls = []
    tracking_calls = []
    job_calls = []

    class FakeManagementService:
        def update_fornecedor(self, **kwargs):
            management_calls.append(("update_fornecedor", kwargs))
            return {"updated": kwargs["fornecedor_id"]}

        def delete_fornecedor(self, **kwargs):
            management_calls.append(("delete_fornecedor", kwargs))
            return {"deleted": kwargs["fornecedor_id"]}

    class FakePreviewService:
        async def preview_pages(self, **kwargs):
            preview_calls.append(("preview_pages", kwargs))
            return {"pages": True}

        def preview_catalog_from_region(self, **kwargs):
            preview_calls.append(("preview_catalog_from_region", kwargs))
            return {"region": kwargs["region"]}

        def extract_data_from_pdf_bulk(self, **kwargs):
            preview_calls.append(("extract_data_from_pdf_bulk", kwargs))
            return {"bulk": kwargs["file_id"]}

    class FakeTrackingService:
        def get_catalog_record_or_404(self, **kwargs):
            tracking_calls.append(("get_catalog_record_or_404", kwargs))
            return SimpleNamespace(id=kwargs["file_id"], status="PROCESSING")

        def build_progress_payload(self, **kwargs):
            tracking_calls.append(("build_progress_payload", kwargs))
            return {"progress": kwargs["record"].id}

        def build_import_job_status_payload(self, **kwargs):
            tracking_calls.append(("build_import_job_status_payload", kwargs))
            return {"status": kwargs["record"].status}

        def schedule_page_extraction(self, **kwargs):
            tracking_calls.append(("schedule_page_extraction", kwargs))
            return None

    class FakeJobService:
        def get_job_for_user_or_404(self, **kwargs):
            job_calls.append(("get_job_for_user_or_404", kwargs))
            return SimpleNamespace(id=kwargs["job_id"])

        def build_review_payload(self, **kwargs):
            job_calls.append(("build_review_payload", kwargs))
            return {"review": kwargs["job"].id}

        def schedule_commit(self, **kwargs):
            job_calls.append(("schedule_commit", kwargs))
            return None

    gateway = object.__new__(fornecedores_module._FornecedoresServiceGateway)
    gateway._fornecedor_preview_service = FakePreviewService()
    gateway._fornecedor_import_tracking_service = FakeTrackingService()
    gateway._fornecedor_import_job_service = FakeJobService()

    current_user = SimpleNamespace(id=7)
    management_service = FakeManagementService()

    assert gateway.update_fornecedor(
        fornecedor_id=12,
        fornecedor_update=_fornecedor_update(),
        current_user=current_user,
        fornecedor_management_service=management_service,
    ) == {"updated": 12}
    assert await gateway.preview_pages(file="arquivo.pdf") == {"pages": True}
    assert gateway.preview_catalog_from_region(
        file_id=9,
        page_number=2,
        region=[1.0, 2.0, 3.0, 4.0],
    ) == {"region": [1.0, 2.0, 3.0, 4.0]}
    assert gateway.extract_data_from_pdf_bulk(
        background_tasks="bg",
        file_id=11,
        region=[0.1, 0.2, 0.3, 0.4],
        pages=[1, 2],
        all_pages=False,
    ) == {"bulk": 11}
    record = gateway.get_catalog_record_or_404(
        file_id=5,
        user_id=7,
        not_found_detail="x",
    )
    assert gateway.build_progress_payload(record=record) == {"progress": 5}
    assert gateway.delete_fornecedor(
        fornecedor_id=14,
        current_user=current_user,
        fornecedor_management_service=management_service,
    ) == {"deleted": 14}
    job = gateway.get_job_for_user_or_404(job_id=20, user_id=7)
    assert gateway.build_review_payload(job=job) == {"review": 20}
    assert gateway.schedule_commit(background_tasks="bg", job_id=20, user_id=7) is None
    assert gateway.build_import_job_status_payload(record=record) == {"status": "PROCESSING"}

    assert any(name == "update_fornecedor" for name, _payload in management_calls)
    assert any(name == "preview_pages" for name, _payload in preview_calls)
    assert any(name == "build_progress_payload" for name, _payload in tracking_calls)
    assert any(name == "schedule_commit" for name, _payload in job_calls)


def test_fornecedores_request_service_covers_sync_delegate_paths():
    calls = []

    class FakeRuntime:
        def create_fornecedor(self, **kwargs):
            calls.append(("create_fornecedor", kwargs))
            return "created"

        def list_fornecedores_page(self, **kwargs):
            calls.append(("list_fornecedores_page", kwargs))
            return {"items": []}

        def resolve_fornecedor_for_user(self, **kwargs):
            calls.append(("resolve_fornecedor_for_user", kwargs))
            return "resolved"

        def update_fornecedor(self, **kwargs):
            calls.append(("update_fornecedor", kwargs))
            return "updated"

        def get_mapping(self, **kwargs):
            calls.append(("get_mapping", kwargs))
            return {"coluna": "nome"}

        def update_mapping(self, **kwargs):
            calls.append(("update_mapping", kwargs))
            return "mapping-updated"

        def preview_catalog_from_region(self, **kwargs):
            calls.append(("preview_catalog_from_region", kwargs))
            return {"preview": True}

        def extract_data_from_pdf_bulk(self, **kwargs):
            calls.append(("extract_data_from_pdf_bulk", kwargs))
            return {"job_id": 55}

        def get_catalog_record_or_404(self, **kwargs):
            calls.append(("get_catalog_record_or_404", kwargs))
            return SimpleNamespace(id=99)

        def build_progress_payload(self, **kwargs):
            calls.append(("build_progress_payload", kwargs))
            return {"progress": kwargs["record"].id}

        def schedule_page_extraction(self, **kwargs):
            calls.append(("schedule_page_extraction", kwargs))

        def delete_fornecedor(self, **kwargs):
            calls.append(("delete_fornecedor", kwargs))
            return "deleted"

        def get_job_for_user_or_404(self, **kwargs):
            calls.append(("get_job_for_user_or_404", kwargs))
            return SimpleNamespace(id=111)

        def build_review_payload(self, **kwargs):
            calls.append(("build_review_payload", kwargs))
            return {"review": kwargs["job"].id}

        def schedule_commit(self, **kwargs):
            calls.append(("schedule_commit", kwargs))

        def build_import_job_status_payload(self, **kwargs):
            calls.append(("build_import_job_status_payload", kwargs))
            return {"status": kwargs["record"].id}

    service = fornecedores_module.FornecedoresRequestService(runtime=FakeRuntime())
    current_user = SimpleNamespace(id=7)
    management_service = object()
    background_tasks = object()
    region_request = SimpleNamespace(file_id=1, page_number=2, region=[1.0, 2.0, 3.0, 4.0])
    bulk_request = SimpleNamespace(file_id=10, region=[1, 2, 3, 4], pages=[1, 2], all_pages=False)

    assert service.create_fornecedor(_fornecedor_create(), current_user, management_service) == "created"
    assert service.list_fornecedores_page(current_user, 0, 10, "busca", management_service) == {"items": []}
    assert service.read_fornecedor(9, current_user, management_service) == "resolved"
    assert service.update_fornecedor(9, _fornecedor_update(), current_user, management_service) == "updated"
    assert service.get_mapping(9, current_user, management_service) == {"coluna": "nome"}
    assert service.update_mapping(9, {"x": "y"}, current_user, management_service) == "mapping-updated"
    assert service.preview_catalog_from_region(region_request) == {"preview": True}
    assert service.extract_data_from_pdf_bulk(background_tasks, bulk_request) == {"job_id": 55}
    assert service.get_import_progress(12, current_user) == {"progress": 99}
    assert service.extract_page_data(background_tasks, 12, 5, current_user) == {"job_id": 99, "status": "PROCESSING"}
    assert service.delete_fornecedor(9, current_user, management_service) == "deleted"
    assert service.review_import_job(33, current_user) == {"review": 111}
    assert service.commit_import_job(background_tasks, 33, current_user) == {"status": "PROCESSING", "job_id": 33}
    assert service.get_import_job_status(33, current_user) == {"status": 99}
    assert any(name == "schedule_page_extraction" for name, _payload in calls)
    assert any(name == "schedule_commit" for name, _payload in calls)


@pytest.mark.asyncio
async def test_fornecedores_request_service_covers_async_delegate_paths():
    calls = []

    class FakeRuntime:
        async def preview_pages(self, **kwargs):
            calls.append(("preview_pages", kwargs))
            return {"preview_pages": True}

        def resolve_fornecedor_for_user(self, **kwargs):
            calls.append(("resolve_fornecedor_for_user", kwargs))
            return "fornecedor"

        def preview_pdf(self, **kwargs):
            calls.append(("preview_pdf", kwargs))
            return {"preview_pdf": kwargs["fornecedor_id"]}

        async def start_full_processing(self, **kwargs):
            calls.append(("start_full_processing", kwargs))
            return {"started": kwargs["file_id"]}

    service = fornecedores_module.FornecedoresRequestService(runtime=FakeRuntime())
    current_user = SimpleNamespace(id=44)
    management_service = object()

    assert await service.preview_pages(file="arquivo.pdf") == {"preview_pages": True}
    assert await service.preview_pdf(
        fornecedor_id=8,
        file="arquivo.pdf",
        current_user=current_user,
        offset=0,
        limit=20,
        fornecedor_management_service=management_service,
    ) == {"preview_pdf": 8}
    assert await service.process_full_catalog(
        background_tasks="bg",
        file_id=10,
        fornecedor_id=8,
        tipo_produto_id=3,
        start_page=1,
        region=[1.0, 2.0, 3.0, 4.0],
        mapping={"nome": "Nome Base"},
        current_user=current_user,
    ) == {"started": 10}
    assert calls[1][0] == "resolve_fornecedor_for_user"


@pytest.mark.asyncio
async def test_fornecedores_request_scope_and_endpoint_handlers_delegate(monkeypatch):
    scope_calls = []

    class FakeRequestService:
        def __init__(self, runtime=None):
            _ = runtime

        def create_fornecedor(self, **kwargs):
            scope_calls.append(("create_fornecedor", kwargs))
            return "created"

        def list_fornecedores_page(self, **kwargs):
            scope_calls.append(("list_fornecedores_page", kwargs))
            return {"items": []}

        def read_fornecedor(self, **kwargs):
            scope_calls.append(("read_fornecedor", kwargs))
            return "read"

        def update_fornecedor(self, **kwargs):
            scope_calls.append(("update_fornecedor", kwargs))
            return "updated"

        def get_mapping(self, **kwargs):
            scope_calls.append(("get_mapping", kwargs))
            return {"mapping": True}

        def update_mapping(self, **kwargs):
            scope_calls.append(("update_mapping", kwargs))
            return "mapping-updated"

        async def preview_pages(self, **kwargs):
            scope_calls.append(("preview_pages", kwargs))
            return {"pages": True}

        async def preview_pdf(self, **kwargs):
            scope_calls.append(("preview_pdf", kwargs))
            return {"pdf": True}

        def preview_catalog_from_region(self, **kwargs):
            scope_calls.append(("preview_catalog_from_region", kwargs))
            return {"region": True}

        def extract_data_from_pdf_bulk(self, **kwargs):
            scope_calls.append(("extract_data_from_pdf_bulk", kwargs))
            return {"bulk": True}

        def get_import_progress(self, **kwargs):
            scope_calls.append(("get_import_progress", kwargs))
            return {"progress": True}

        async def process_full_catalog(self, **kwargs):
            scope_calls.append(("process_full_catalog", kwargs))
            return {"process": True}

        def extract_page_data(self, **kwargs):
            scope_calls.append(("extract_page_data", kwargs))
            return {"page": True}

        def delete_fornecedor(self, **kwargs):
            scope_calls.append(("delete_fornecedor", kwargs))
            return "deleted"

        def review_import_job(self, **kwargs):
            scope_calls.append(("review_import_job", kwargs))
            return {"review": True}

        def commit_import_job(self, **kwargs):
            scope_calls.append(("commit_import_job", kwargs))
            return {"commit": True}

        def get_import_job_status(self, **kwargs):
            scope_calls.append(("get_import_job_status", kwargs))
            return {"status": True}

    monkeypatch.setattr(
        fornecedores_module._FornecedoresDependencies,
        "get_fornecedores_request_service",
        staticmethod(lambda session: scope_calls.append(("request_service_init", session)) or FakeRequestService()),
    )

    request_scope = fornecedores_module._FornecedoresRequestScope(
        session="db",
        fornecedor_management_service="management-service",
    )
    current_user = SimpleNamespace(id=77)
    background_tasks = object()

    assert request_scope.create_fornecedor(fornecedor=_fornecedor_create(), current_user=current_user) == "created"
    assert request_scope.list_fornecedores_page(current_user=current_user, skip=0, limit=10, termo_busca=None) == {"items": []}
    assert request_scope.read_fornecedor(fornecedor_id=1, current_user=current_user) == "read"
    assert request_scope.update_fornecedor(fornecedor_id=1, fornecedor_update=_fornecedor_update(), current_user=current_user) == "updated"
    assert request_scope.get_mapping(fornecedor_id=1, current_user=current_user) == {"mapping": True}
    assert request_scope.update_mapping(fornecedor_id=1, mapping={"x": "y"}, current_user=current_user) == "mapping-updated"
    assert await request_scope.preview_pages(file="arquivo.pdf") == {"pages": True}
    assert await request_scope.preview_pdf(fornecedor_id=1, file="arquivo.pdf", current_user=current_user, offset=0, limit=20) == {"pdf": True}
    assert request_scope.preview_catalog_from_region(preview_request="preview-request") == {"region": True}
    assert request_scope.extract_data_from_pdf_bulk(background_tasks=background_tasks, request="bulk-request") == {"bulk": True}
    assert request_scope.get_import_progress(job_id=1, current_user=current_user) == {"progress": True}
    assert await request_scope.process_full_catalog(background_tasks=background_tasks, file_id=1, fornecedor_id=2, tipo_produto_id=3, start_page=1, region=None, mapping=None, current_user=current_user) == {"process": True}
    assert request_scope.extract_page_data(background_tasks=background_tasks, file_id=1, page_number=2, current_user=current_user) == {"page": True}
    assert request_scope.delete_fornecedor(fornecedor_id=1, current_user=current_user) == "deleted"
    assert request_scope.review_import_job(job_id=1, current_user=current_user) == {"review": True}
    assert request_scope.commit_import_job(background_tasks=background_tasks, job_id=1, current_user=current_user) == {"commit": True}
    assert request_scope.get_import_job_status(job_id=1, current_user=current_user) == {"status": True}

    class FakeEndpointScope:
        def create_fornecedor(self, **kwargs):
            return kwargs["fornecedor"]

        def list_fornecedores_page(self, **kwargs):
            return kwargs

        def read_fornecedor(self, **kwargs):
            return kwargs["fornecedor_id"]

        def update_fornecedor(self, **kwargs):
            return kwargs["fornecedor_update"]

        def get_mapping(self, **kwargs):
            return {"mapping": kwargs["fornecedor_id"]}

        def update_mapping(self, **kwargs):
            return kwargs["mapping"]

        async def preview_pages(self, **kwargs):
            return {"file": kwargs["file"]}

        async def preview_pdf(self, **kwargs):
            return {"preview": kwargs["fornecedor_id"]}

        def preview_catalog_from_region(self, **kwargs):
            return kwargs["preview_request"]

        def extract_data_from_pdf_bulk(self, **kwargs):
            return kwargs["request"]

        def get_import_progress(self, **kwargs):
            return {"progress": kwargs["job_id"]}

        async def process_full_catalog(self, **kwargs):
            return {"process": kwargs["file_id"]}

        def extract_page_data(self, **kwargs):
            return {"page": kwargs["page_number"]}

        def delete_fornecedor(self, **kwargs):
            return {"deleted": kwargs["fornecedor_id"]}

        def review_import_job(self, **kwargs):
            return {"review": kwargs["job_id"]}

        def commit_import_job(self, **kwargs):
            return {"commit": kwargs["job_id"]}

        def get_import_job_status(self, **kwargs):
            return {"status": kwargs["job_id"]}

    endpoint_scope = FakeEndpointScope()
    fornecedor = _fornecedor_create()
    updated = _fornecedor_update()
    preview_request = SimpleNamespace(file_id=1, page_number=2, region=[0.1, 0.2, 0.3, 0.4])
    bulk_request = SimpleNamespace(file_id=2, region=[1, 2, 3, 4], pages=None, all_pages=True)

    assert fornecedores_module._EndpointHandlers.create_user_fornecedor(
        fornecedor=fornecedor,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) is fornecedor
    assert fornecedores_module._EndpointHandlers.read_user_fornecedores(
        skip=0,
        limit=10,
        termo_busca="busca",
        current_user=current_user,
        request_scope=endpoint_scope,
    )["termo_busca"] == "busca"
    assert fornecedores_module._EndpointHandlers.read_fornecedor(
        fornecedor_id=9,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == 9
    assert fornecedores_module._EndpointHandlers.update_fornecedor_endpoint(
        fornecedor_id=9,
        fornecedor_update=updated,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) is updated
    assert fornecedores_module._EndpointHandlers.get_mapping(
        fornecedor_id=9,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"mapping": 9}
    assert fornecedores_module._EndpointHandlers.update_mapping(
        fornecedor_id=9,
        mapping={"x": "y"},
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"x": "y"}
    assert await fornecedores_module._EndpointHandlers.preview_pages(file="arquivo.pdf", request_scope=endpoint_scope) == {"file": "arquivo.pdf"}
    assert await fornecedores_module._EndpointHandlers.preview_pdf(
        fornecedor_id=9,
        file="arquivo.pdf",
        current_user=current_user,
        request_scope=endpoint_scope,
        offset=0,
        limit=20,
    ) == {"preview": 9}
    assert fornecedores_module._EndpointHandlers.preview_catalog_from_region(preview_request=preview_request, request_scope=endpoint_scope) is preview_request
    assert fornecedores_module._EndpointHandlers.extract_data_from_pdf_bulk(
        background_tasks=background_tasks,
        request=bulk_request,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) is bulk_request
    assert fornecedores_module._EndpointHandlers.get_import_progress(
        job_id=4,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"progress": 4}
    assert await fornecedores_module._EndpointHandlers.process_full_catalog(
        background_tasks=background_tasks,
        file_id=5,
        fornecedor_id=6,
        tipo_produto_id=7,
        start_page=1,
        region=None,
        mapping=None,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"process": 5}
    assert fornecedores_module._EndpointHandlers.extract_page_data(
        background_tasks=background_tasks,
        file_id=5,
        page_number=2,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"page": 2}
    assert fornecedores_module._EndpointHandlers.delete_fornecedor_endpoint(
        fornecedor_id=6,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"deleted": 6}
    assert fornecedores_module._EndpointHandlers.review_import_job(
        job_id=8,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"review": 8}
    assert fornecedores_module._EndpointHandlers.commit_import_job(
        background_tasks=background_tasks,
        job_id=8,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"commit": 8}
    assert fornecedores_module._EndpointHandlers.get_import_job_status(
        job_id=8,
        current_user=current_user,
        request_scope=endpoint_scope,
    ) == {"status": 8}


def test_fornecedores_endpoint_handlers_preserve_http_exceptions_and_wrap_generic_errors(monkeypatch):
    logger_calls = []
    monkeypatch.setattr(fornecedores_module.logger, "warning", lambda *args, **kwargs: logger_calls.append(("warning", args, kwargs)))
    monkeypatch.setattr(fornecedores_module.logger, "exception", lambda *args, **kwargs: logger_calls.append(("exception", args, kwargs)))
    current_user = SimpleNamespace(id=1)
    fornecedor = _fornecedor_create()
    update = _fornecedor_update()

    class HttpErrorScope:
        def create_fornecedor(self, **kwargs):
            _ = kwargs
            raise HTTPException(status_code=400, detail="fornecedor invalido")

        def update_fornecedor(self, **kwargs):
            _ = kwargs
            raise HTTPException(status_code=404, detail="nao encontrado")

        def delete_fornecedor(self, **kwargs):
            _ = kwargs
            raise HTTPException(status_code=403, detail="proibido")

    with pytest.raises(HTTPException) as create_exc:
        fornecedores_module._EndpointHandlers.create_user_fornecedor(
            fornecedor=fornecedor,
            current_user=current_user,
            request_scope=HttpErrorScope(),
        )
    assert create_exc.value.status_code == 400

    with pytest.raises(HTTPException) as update_exc:
        fornecedores_module._EndpointHandlers.update_fornecedor_endpoint(
            fornecedor_id=9,
            fornecedor_update=update,
            current_user=current_user,
            request_scope=HttpErrorScope(),
        )
    assert update_exc.value.status_code == 404

    with pytest.raises(HTTPException) as delete_exc:
        fornecedores_module._EndpointHandlers.delete_fornecedor_endpoint(
            fornecedor_id=9,
            current_user=current_user,
            request_scope=HttpErrorScope(),
        )
    assert delete_exc.value.status_code == 403

    class GenericErrorScope:
        def create_fornecedor(self, **kwargs):
            _ = kwargs
            raise RuntimeError("boom-create")

        def update_fornecedor(self, **kwargs):
            _ = kwargs
            raise RuntimeError("boom-update")

        def delete_fornecedor(self, **kwargs):
            _ = kwargs
            raise RuntimeError("boom-delete")

    with pytest.raises(HTTPException) as create_exc:
        fornecedores_module._EndpointHandlers.create_user_fornecedor(
            fornecedor=fornecedor,
            current_user=current_user,
            request_scope=GenericErrorScope(),
        )
    assert create_exc.value.status_code == 500

    with pytest.raises(HTTPException) as update_exc:
        fornecedores_module._EndpointHandlers.update_fornecedor_endpoint(
            fornecedor_id=9,
            fornecedor_update=update,
            current_user=current_user,
            request_scope=GenericErrorScope(),
        )
    assert update_exc.value.status_code == 500

    with pytest.raises(HTTPException) as delete_exc:
        fornecedores_module._EndpointHandlers.delete_fornecedor_endpoint(
            fornecedor_id=9,
            current_user=current_user,
            request_scope=GenericErrorScope(),
        )
    assert delete_exc.value.status_code == 500
    assert any(kind == "warning" for kind, _args, _kwargs in logger_calls)
    assert any(kind == "exception" for kind, _args, _kwargs in logger_calls)
