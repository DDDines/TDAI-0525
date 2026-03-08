"""Extra coverage for small application service wrappers and DI helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend import schemas
from Backend.application.pipeline_selector import PipelineSelector, TaskExecutionPlan
from Backend.application.services.catalog_import_workflow_service import (
    CatalogImportWorkflowService,
)
from Backend.application.services.file_processing.pdf_ingestion_service import (
    FileProcessingPdfIngestionService,
)
from Backend.application.services.file_processing.storage_service import (
    FileProcessingStorageService,
)
from Backend.application.services import service_container as service_container_module
from Backend.application.services.web_enrichment_task_runner import (
    WebEnrichmentTaskRunner,
)


def test_task_execution_plan_and_pipeline_selector_details(monkeypatch):
    monkeypatch.setattr(
        "Backend.application.pipeline_selector.AppModeWorkflow.get_app_mode",
        lambda self: "oop",
    )

    async def _executor(**kwargs):
        return kwargs

    plan = TaskExecutionPlan(
        name="test",
        executor_name="executor",
        executor=_executor,
        task_kwargs={"produto_id": 7},
    )
    assert plan.to_compare_payload() == {
        "name": "test",
        "executor_name": "executor",
        "task_kwargs": {"produto_id": 7},
    }
    assert PipelineSelector("ctx").select(oop_plan=plan) is plan


def test_service_container_dependency_support_and_dependency_container(monkeypatch):
    dependency = service_container_module.ServiceContainerDependencySupport.build_request_scoped_dependency(
        lambda session: ("factory", session)
    )
    assert dependency(session="db") == ("factory", "db")
    assert (
        service_container_module.ServiceContainerDependencySupport.get_request_db_session(session="db")
        == "db"
    )

    monkeypatch.setattr(
        service_container_module,
        "FileProcessingOrchestratorService",
        lambda port: ("file_processing", port),
    )
    monkeypatch.setattr(
        service_container_module,
        "WebDataExtractorOrchestratorService",
        lambda port: ("web_extractor", port),
    )
    monkeypatch.setattr(
        service_container_module,
        "IAGenerationService",
        lambda port: ("ia_generation", port),
    )
    monkeypatch.setattr(
        service_container_module,
        "LimitService",
        lambda port: ("limit", port),
    )
    monkeypatch.setattr(service_container_module, "FileProcessingServiceAdapter", lambda: "file-port")
    monkeypatch.setattr(service_container_module, "WebDataExtractorServiceAdapter", lambda: "web-port")
    monkeypatch.setattr(service_container_module, "IAGenerationServiceAdapter", lambda: "ia-port")
    monkeypatch.setattr(service_container_module, "LimitServiceAdapter", lambda: "limit-port")
    monkeypatch.setattr(service_container_module.database, "SessionLocal", lambda: "session-local")

    assert service_container_module.ServiceContainerDependencySupport.build_file_processing_service() == (
        "file_processing",
        "file-port",
    )
    assert service_container_module.ServiceContainerDependencySupport.build_web_data_extractor_service() == (
        "web_extractor",
        "web-port",
    )
    assert service_container_module.ServiceContainerDependencySupport.build_ia_generation_service() == (
        "ia_generation",
        "ia-port",
    )
    assert service_container_module.ServiceContainerDependencySupport.build_limit_service() == (
        "limit",
        "limit-port",
    )
    assert isinstance(
        service_container_module.ServiceContainerDependencySupport.get_background_session_provider(),
        service_container_module.SessionProvider,
    )

    with pytest.raises(ValueError):
        service_container_module.ServiceContainerDependencySupport.build_background_session_provider_from_session(
            SimpleNamespace(get_bind=lambda: None)
        )

    provider = service_container_module.ServiceContainerDependencySupport.build_background_session_provider_from_session(
        SimpleNamespace(get_bind=lambda: "engine")
    )
    assert isinstance(provider, service_container_module.SessionProvider)

    session_provider = service_container_module.SessionProvider(lambda: "db-session")
    assert session_provider.open_session() == "db-session"

    monkeypatch.setattr(
        service_container_module.ProductRepositories,
        "build_product_management_repositories",
        staticmethod(lambda session: {"repo": ("management", session)}),
    )
    monkeypatch.setattr(
        service_container_module.ProductRepositories,
        "build_product_media_repositories",
        staticmethod(lambda session: {"repo": ("media", session)}),
    )
    monkeypatch.setattr(
        service_container_module,
        "ProductManagementService",
        lambda **kwargs: ("product_management", kwargs),
    )
    monkeypatch.setattr(
        service_container_module,
        "ProductMediaService",
        lambda **kwargs: ("product_media", kwargs),
    )
    monkeypatch.setattr(
        service_container_module,
        "FornecedorManagementService",
        lambda **kwargs: ("fornecedor_management", kwargs),
    )
    monkeypatch.setattr(service_container_module, "FornecedorRepository", lambda session: ("fornecedor_repo", session))
    monkeypatch.setattr(service_container_module, "HistoricoRepository", lambda session: ("historico_repo", session))

    assert service_container_module.DependencyContainer.get_db_session("db") == "db"
    assert service_container_module.DependencyContainer.get_product_management_service("db")[0] == "product_management"
    assert service_container_module.DependencyContainer.get_product_media_service("db")[0] == "product_media"
    assert service_container_module.DependencyContainer.get_fornecedor_management_service("db")[0] == "fornecedor_management"


@pytest.mark.asyncio
async def test_web_enrichment_task_runner_build_and_execute_paths():
    runner = WebEnrichmentTaskRunner(
        session_provider="session-provider",
        logger="logger",
        SQLAlchemyError=Exception,
        user_repository_factory="user-repo",
        product_repository_factory="product-repo",
        usage_repository_factory="usage-repo",
        models="models",
        schemas="schemas",
        web_extractor="web-extractor",
        settings="settings",
        json_module="json",
        re_module="re",
        normalize_human_text="normalize",
        build_payload_enriquecimento_visivel="payload",
        extrair_dominio_fornecedor="domain",
        priorizar_urls_para_enriquecimento="prioritize",
        is_meaningful_extracted_text="meaningful",
        metadata_has_minimum_signal="signal",
        is_source_relevant_for_product="relevant",
    )

    class FakeTaskService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.calls = []

        async def execute(self, **kwargs):
            self.calls.append(kwargs)

    service = FakeTaskService()
    runner._build = lambda: service  # type: ignore[assignment]
    assert runner._get_service() is service
    await runner.execute(produto_id=1, user_id=2, termos_busca_override="busca")
    assert service.calls == [{"produto_id": 1, "user_id": 2, "termos_busca_override": "busca"}]


def test_web_enrichment_task_runner_build_injects_web_extractor(monkeypatch):
    captured = {}

    class FakeBuiltService:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "Backend.application.services.web_enrichment_task_runner.WebEnrichmentTaskService",
        FakeBuiltService,
    )

    runner = WebEnrichmentTaskRunner(
        session_provider="session-provider",
        logger="logger",
        SQLAlchemyError=Exception,
        user_repository_factory="user-repo",
        product_repository_factory="product-repo",
        usage_repository_factory="usage-repo",
        models="models",
        schemas="schemas",
        web_extractor="web-extractor",
        settings="settings",
        json_module="json",
        re_module="re",
        normalize_human_text="normalize",
        build_payload_enriquecimento_visivel="payload",
        extrair_dominio_fornecedor="domain",
        priorizar_urls_para_enriquecimento="prioritize",
        is_meaningful_extracted_text="meaningful",
        metadata_has_minimum_signal="signal",
        is_source_relevant_for_product="relevant",
    )

    built = runner._build()
    assert isinstance(built, FakeBuiltService)
    assert captured["web_extractor"] == "web-extractor"
    assert captured["session_provider"] == "session-provider"
    assert captured["build_payload_enriquecimento_visivel"] == "payload"


@pytest.mark.asyncio
async def test_catalog_import_workflow_runtime_override_and_direct_delegates():
    runtime = SimpleNamespace(
        start_service=SimpleNamespace(name="start"),
        status_service=SimpleNamespace(name="status"),
    )
    service = CatalogImportWorkflowService(
        start_service="fallback-start",
        status_service="fallback-status",
        runtime=runtime,
    )
    assert service._start_service is runtime.start_service
    assert service._status_service is runtime.status_service

    start_calls = []
    status_calls = []

    class StartStub:
        def get_catalog_file_or_404(self, **kwargs):
            start_calls.append(("get", kwargs))
            return SimpleNamespace(fornecedor_id=3)

        def resolve_fornecedor_id(self, **kwargs):
            start_calls.append(("resolve_fornecedor", kwargs))
            return 3

        def resolve_pdf_pages(self, **kwargs):
            start_calls.append(("resolve_pages", kwargs))
            return [1, 2]

        def resolve_mapping(self, **kwargs):
            start_calls.append(("resolve_mapping", kwargs))
            return {"sku": "sku"}

        def build_finalize_command(self, **kwargs):
            start_calls.append(("build", kwargs))
            return {"command": kwargs}

        async def run_finalize_direct(self, **kwargs):
            start_calls.append(("run_direct", kwargs))

    class StatusStub:
        def get_record_or_404(self, **kwargs):
            status_calls.append(("get", kwargs))
            return SimpleNamespace(result_summary={"ok": True})

    service = CatalogImportWorkflowService(start_service=StartStub(), status_service=StatusStub())
    result = await service.importar_catalogo_finalizar_todas_paginas(
        file_id=9,
        start_page=2,
        mapping={"col": "sku"},
        extraction_mode="ocr",
        user_id=7,
    )
    assert result == {"ok": True}
    assert start_calls[0][0] == "get"
    assert start_calls[-1][0] == "run_direct"
    assert status_calls == [("get", {"file_id": 9, "user_id": 7})]


@pytest.mark.asyncio
async def test_pdf_ingestion_and_storage_services_delegate_all_methods():
    called = []

    class FakePort:
        async def processar_arquivo_pdf(self, **kwargs):
            called.append(("processar_arquivo_pdf", kwargs))
            return [{"ok": True}]

        async def extrair_pagina_pdf(self, **kwargs):
            called.append(("extrair_pagina_pdf", kwargs))
            return {"page": kwargs["page_number"]}

        def extract_data_from_pdf_region(self, **kwargs):
            called.append(("extract_data_from_pdf_region", kwargs))
            return "dataframe"

        async def process_pdf_job(self, **kwargs):
            called.append(("process_pdf_job", kwargs))
            return None

        def extract_data_from_single_page(self, **kwargs):
            called.append(("extract_data_from_single_page", kwargs))
            return {"page": kwargs["page_number"]}

        async def save_uploaded_catalog(self, **kwargs):
            called.append(("save_uploaded_catalog", kwargs))
            return {"stored_filename": "arquivo.pdf"}

        def delete_catalog_file(self, **kwargs):
            called.append(("delete_catalog_file", kwargs))
            return None

        def get_file_path_by_id(self, **kwargs):
            called.append(("get_file_path_by_id", kwargs))
            return "/tmp/catalogo.pdf"

    port = FakePort()
    pdf_service = FileProcessingPdfIngestionService(port)
    storage_service = FileProcessingStorageService(port)

    assert await pdf_service.processar_arquivo_pdf(b"%PDF") == [{"ok": True}]
    assert await pdf_service.extrair_pagina_pdf(b"%PDF", page_number=2) == {"page": 2}
    assert pdf_service.extract_data_from_pdf_region("file.pdf", page_number=2) == "dataframe"
    assert await pdf_service.process_pdf_job(job_id=1, pdf_path="file.pdf") is None
    assert pdf_service.extract_data_from_single_page("file.pdf", page_number=3) == {"page": 3}
    assert await storage_service.save_uploaded_catalog(file="file") == {"stored_filename": "arquivo.pdf"}
    assert storage_service.delete_catalog_file("arquivo.pdf") is None
    assert storage_service.get_file_path_by_id(db="db", file_id=1) == "/tmp/catalogo.pdf"

    assert called[0][0] == "processar_arquivo_pdf"
    assert called[-1][0] == "get_file_path_by_id"
