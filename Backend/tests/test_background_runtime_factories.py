"""Tests for shared background runtime factories."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.services import background_runtime_factories as factories


def test_background_session_provider_delegates_to_service_container(monkeypatch):
    monkeypatch.setattr(
        factories.ServiceContainerDependencySupport,
        "get_background_session_provider",
        staticmethod(lambda: "provider"),
    )

    assert factories.background_session_provider() == "provider"


def test_build_web_enrichment_task_runner(monkeypatch):
    monkeypatch.setattr(factories, "background_session_provider", lambda: "provider")
    monkeypatch.setattr(factories, "WebEnrichmentNormalizationService", lambda: SimpleNamespace(normalize_human_text="normalize"))
    monkeypatch.setattr(
        factories,
        "WebEnrichmentRelevanceService",
        lambda: SimpleNamespace(
            extract_supplier_domain="domain",
            prioritize_urls_for_enrichment="prioritize",
            is_source_relevant_for_product="relevant",
        ),
    )
    monkeypatch.setattr(
        factories,
        "WebEnrichmentContentQualityService",
        lambda normalization_service: SimpleNamespace(
            normalization_service=normalization_service,
            is_meaningful_extracted_text="meaningful",
            metadata_has_minimum_signal="signal",
        ),
    )
    monkeypatch.setattr(
        factories,
        "WebEnrichmentPayloadService",
        lambda normalization_service: SimpleNamespace(
            normalization_service=normalization_service,
            build_payload_enriquecimento_visivel="payload",
        ),
    )
    monkeypatch.setattr(factories, "ServiceContainer", lambda: SimpleNamespace(web_data_extractor="web-extractor"))
    monkeypatch.setattr(factories, "WebEnrichmentTaskRunner", lambda **kwargs: ("web-runner", kwargs))

    runner = factories.build_web_enrichment_task_runner()

    assert runner[0] == "web-runner"
    assert runner[1]["session_provider"] == "provider"
    assert runner[1]["web_extractor"] == "web-extractor"


def test_build_web_enrichment_task_runner_honors_explicit_session_provider(monkeypatch):
    monkeypatch.setattr(factories, "WebEnrichmentNormalizationService", lambda: SimpleNamespace(normalize_human_text="normalize"))
    monkeypatch.setattr(
        factories,
        "WebEnrichmentRelevanceService",
        lambda: SimpleNamespace(
            extract_supplier_domain="domain",
            prioritize_urls_for_enrichment="prioritize",
            is_source_relevant_for_product="relevant",
        ),
    )
    monkeypatch.setattr(
        factories,
        "WebEnrichmentContentQualityService",
        lambda normalization_service: SimpleNamespace(
            normalization_service=normalization_service,
            is_meaningful_extracted_text="meaningful",
            metadata_has_minimum_signal="signal",
        ),
    )
    monkeypatch.setattr(
        factories,
        "WebEnrichmentPayloadService",
        lambda normalization_service: SimpleNamespace(
            normalization_service=normalization_service,
            build_payload_enriquecimento_visivel="payload",
        ),
    )
    monkeypatch.setattr(factories, "ServiceContainer", lambda: SimpleNamespace(web_data_extractor="web-extractor"))
    monkeypatch.setattr(factories, "WebEnrichmentTaskRunner", lambda **kwargs: ("web-runner", kwargs))

    runner = factories.build_web_enrichment_task_runner(session_provider="explicit-provider")

    assert runner[1]["session_provider"] == "explicit-provider"


def test_build_catalog_import_task_runner(monkeypatch):
    monkeypatch.setattr(factories, "background_session_provider", lambda: "provider")
    monkeypatch.setattr(factories, "ServiceContainer", lambda: SimpleNamespace(file_processing="file-processing"))
    monkeypatch.setattr(factories, "CatalogImportQualityService", lambda: SimpleNamespace(classify_product_row_quality="quality"))
    monkeypatch.setattr(
        factories,
        "CatalogImportSanitizationService",
        lambda quality_service: SimpleNamespace(
            quality_service=quality_service,
            normalize_import_issue_item="issue",
            extract_import_error_reason="reason",
            is_non_critical_import_reason="non-critical",
            normalize_validated_data="normalize",
            sanitize_extracted_product="sanitize",
            normalize_import_text="normalize-text",
        ),
    )
    monkeypatch.setattr(
        factories,
        "CatalogImportDiagnosticsService",
        lambda **kwargs: SimpleNamespace(
            resolve_storage_path="storage",
            write_catalog_import_report="report",
        ),
    )
    monkeypatch.setattr(factories, "ValidatorCrewService", lambda logger: SimpleNamespace(logger=logger))
    monkeypatch.setattr(factories, "CatalogImportTaskRunner", lambda **kwargs: ("catalog-runner", kwargs))

    runner = factories.build_catalog_import_task_runner()

    assert runner[0] == "catalog-runner"
    assert runner[1]["session_provider"] == "provider"
    assert runner[1]["file_processing_service"] == "file-processing"


def test_build_catalog_import_task_runner_honors_explicit_session_provider(monkeypatch):
    monkeypatch.setattr(factories, "ServiceContainer", lambda: SimpleNamespace(file_processing="file-processing"))
    monkeypatch.setattr(factories, "CatalogImportQualityService", lambda: SimpleNamespace(classify_product_row_quality="quality"))
    monkeypatch.setattr(
        factories,
        "CatalogImportSanitizationService",
        lambda quality_service: SimpleNamespace(
            quality_service=quality_service,
            normalize_import_issue_item="issue",
            extract_import_error_reason="reason",
            is_non_critical_import_reason="non-critical",
            normalize_validated_data="normalize",
            sanitize_extracted_product="sanitize",
            normalize_import_text="normalize-text",
        ),
    )
    monkeypatch.setattr(
        factories,
        "CatalogImportDiagnosticsService",
        lambda **kwargs: SimpleNamespace(
            resolve_storage_path="storage",
            write_catalog_import_report="report",
        ),
    )
    monkeypatch.setattr(factories, "ValidatorCrewService", lambda logger: SimpleNamespace(logger=logger))
    monkeypatch.setattr(factories, "CatalogImportTaskRunner", lambda **kwargs: ("catalog-runner", kwargs))

    runner = factories.build_catalog_import_task_runner(session_provider="explicit-provider")

    assert runner[1]["session_provider"] == "explicit-provider"


def test_build_generation_task_service(monkeypatch):
    monkeypatch.setattr(factories, "background_session_provider", lambda: "provider")
    monkeypatch.setattr(factories, "GenerationTaskService", lambda **kwargs: ("generation-service", kwargs))

    service = factories.build_generation_task_service()

    assert service == (
        "generation-service",
        {
            "session_provider": "provider",
            "user_repository_factory": factories.UserRepository,
            "product_repository_factory": factories.ProductRepository,
            "models": factories.models,
            "schemas": factories.schemas,
            "logger": factories.logger,
        },
    )


def test_resolve_generation_callable_maps_known_providers(monkeypatch):
    ia_service = SimpleNamespace(
        gerar_titulos_com_openai="openai-title",
        gerar_descricao_com_openai="openai-description",
        gerar_titulos_com_gemini="gemini-title",
        gerar_descricao_com_gemini="gemini-description",
    )
    basic_service = SimpleNamespace(
        gerar_titulos_basicos="basic-title",
        gerar_descricao_basica="basic-description",
    )
    monkeypatch.setattr(
        factories.ServiceContainerDependencySupport,
        "build_ia_generation_service",
        staticmethod(lambda: ia_service),
    )
    monkeypatch.setattr(factories, "BasicContentGenerationService", lambda: basic_service)

    assert factories.resolve_generation_callable("openai_title") == "openai-title"
    assert factories.resolve_generation_callable("openai_description") == "openai-description"
    assert factories.resolve_generation_callable("gemini_title") == "gemini-title"
    assert factories.resolve_generation_callable("gemini_description") == "gemini-description"
    assert factories.resolve_generation_callable("basic_title") == "basic-title"
    assert factories.resolve_generation_callable("basic_description") == "basic-description"

    with pytest.raises(ValueError):
        factories.resolve_generation_callable("missing")


def test_build_fornecedor_import_job_service(monkeypatch):
    monkeypatch.setattr(factories, "background_session_provider", lambda: "provider")
    captured = {}

    class _Service:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "Backend.application.services.fornecedor_import_job_service.FornecedorImportJobService",
        _Service,
    )

    service = factories.build_fornecedor_import_job_service()

    assert isinstance(service, _Service)
    assert captured["session_provider"] == "provider"
    assert captured["produto_create_schema"] == factories.schemas.ProdutoCreate


def test_build_fornecedor_import_job_service_honors_explicit_session_provider(monkeypatch):
    captured = {}

    class _Service:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "Backend.application.services.fornecedor_import_job_service.FornecedorImportJobService",
        _Service,
    )

    service = factories.build_fornecedor_import_job_service(session_provider="explicit-provider")

    assert isinstance(service, _Service)
    assert captured["session_provider"] == "explicit-provider"


def test_build_pdf_region_extractor(monkeypatch):
    extractor = lambda **kwargs: kwargs
    monkeypatch.setattr(factories, "ServiceContainer", lambda: SimpleNamespace(file_processing=SimpleNamespace(extract_data_from_pdf_region=extractor)))

    assert factories.build_pdf_region_extractor() is extractor
