"""Factories for background and Celery runtime composition."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, Callable

from sqlalchemy.exc import SQLAlchemyError

from Backend import models, schemas
from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)
from Backend.application.services.catalog_import_diagnostics_service import (
    CatalogImportDiagnosticsService,
)
from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)
from Backend.application.services.catalog_import_task_runner import (
    CatalogImportTaskRunner,
)
from Backend.application.services.generation_task_service import GenerationTaskService
from Backend.application.services.service_container import (
    ServiceContainer,
    ServiceContainerDependencySupport,
)
from Backend.application.services.validator_crew_service import ValidatorCrewService
from Backend.application.services.web_enrichment_content_quality_service import (
    WebEnrichmentContentQualityService,
)
from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.application.services.web_enrichment_payload_service import (
    WebEnrichmentPayloadService,
)
from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)
from Backend.application.services.web_enrichment_task_runner import (
    WebEnrichmentTaskRunner,
)
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.catalog_import_file_repository import (
    CatalogImportFileRepository,
)
from Backend.infrastructure.repositories.fornecedor_import_job_repository import (
    FornecedorImportJobRepository,
)
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository


logger = get_logger(__name__)
catalog_log_dir = Path(__file__).resolve().parents[2] / "logs"
catalog_log_dir.mkdir(parents=True, exist_ok=True)


class BackgroundRuntimeFactories:
    """Centralize construction of shared background runtimes."""

    @staticmethod
    def background_session_provider() -> Any:
        """Build the shared background session provider."""
        return ServiceContainerDependencySupport.get_background_session_provider()

    @staticmethod
    def build_web_enrichment_task_runner(
        *,
        session_provider: Any | None = None,
    ) -> WebEnrichmentTaskRunner:
        """Compose the web enrichment runner used by background backends."""
        normalization_service = WebEnrichmentNormalizationService()
        relevance_service = WebEnrichmentRelevanceService()
        content_quality_service = WebEnrichmentContentQualityService(
            normalization_service=normalization_service
        )
        payload_service = WebEnrichmentPayloadService(
            normalization_service=normalization_service
        )
        service_container = ServiceContainer()
        return WebEnrichmentTaskRunner(
            session_provider=session_provider or background_session_provider(),
            logger=logger,
            SQLAlchemyError=SQLAlchemyError,
            user_repository_factory=UserRepository,
            product_repository_factory=ProductRepository,
            usage_repository_factory=RegistroUsoIARepository,
            models=models,
            schemas=schemas,
            web_extractor=service_container.web_data_extractor,
            settings=settings,
            json_module=json,
            re_module=re,
            normalize_human_text=normalization_service.normalize_human_text,
            build_payload_enriquecimento_visivel=payload_service.build_payload_enriquecimento_visivel,
            extrair_dominio_fornecedor=relevance_service.extract_supplier_domain,
            priorizar_urls_para_enriquecimento=relevance_service.prioritize_urls_for_enrichment,
            is_meaningful_extracted_text=content_quality_service.is_meaningful_extracted_text,
            metadata_has_minimum_signal=content_quality_service.metadata_has_minimum_signal,
            is_source_relevant_for_product=relevance_service.is_source_relevant_for_product,
        )

    @staticmethod
    def build_catalog_import_task_runner(
        *,
        session_provider: Any | None = None,
    ) -> CatalogImportTaskRunner:
        """Compose the catalog import runner used by background backends."""
        from Backend.application.services.file_processing.vision_extraction_service import (
            VisionExtractionService,
        )
        from Backend.infrastructure.adapters.vision_extraction_adapter import (
            VisionExtractionServiceAdapter,
        )

        service_container = ServiceContainer()
        quality_service = CatalogImportQualityService()
        sanitization_service = CatalogImportSanitizationService(
            quality_service=quality_service
        )
        diagnostics_service = CatalogImportDiagnosticsService(
            catalog_log_dir=catalog_log_dir,
            logger=logger,
            sanitization_service=sanitization_service,
        )
        validator_crew = ValidatorCrewService(logger=logger)
        vision_service = VisionExtractionService(VisionExtractionServiceAdapter())
        return CatalogImportTaskRunner(
            session_provider=session_provider or background_session_provider(),
            logger=logger,
            catalog_logger=logger,
            models=models,
            schemas=schemas,
            product_repository_factory=ProductRepository,
            catalog_file_repository_factory=CatalogImportFileRepository,
            file_processing_service=service_container.file_processing,
            validator_crew=validator_crew,
            settings=settings,
            path_cls=Path,
            time_module=time,
            counter_cls=Counter,
            resolve_storage_path=diagnostics_service.resolve_storage_path,
            normalize_import_issue_item=sanitization_service.normalize_import_issue_item,
            extract_import_error_reason=sanitization_service.extract_import_error_reason,
            is_non_critical_import_reason=sanitization_service.is_non_critical_import_reason,
            normalizar_dados_validados=sanitization_service.normalize_validated_data,
            sanitize_produto_extraido=sanitization_service.sanitize_extracted_product,
            classificar_qualidade_linha_produto=quality_service.classify_product_row_quality,
            write_catalog_import_report=diagnostics_service.write_catalog_import_report,
            normalize_import_text=sanitization_service.normalize_import_text,
            vision_service=vision_service,
        )

    @staticmethod
    def build_generation_task_service() -> GenerationTaskService:
        """Compose the generation task service used by background backends."""
        return GenerationTaskService(
            session_provider=background_session_provider(),
            user_repository_factory=UserRepository,
            product_repository_factory=ProductRepository,
            models=models,
            schemas=schemas,
            logger=logger,
        )

    @staticmethod
    def resolve_generation_callable(provider_key: str) -> Callable[..., Any]:
        """Resolve a serializable generation provider key into an async callable."""
        ia_service = ServiceContainerDependencySupport.build_ia_generation_service()
        basic_service = BasicContentGenerationService()
        mapping = {
            "openai_title": ia_service.gerar_titulos_com_openai,
            "openai_description": ia_service.gerar_descricao_com_openai,
            "gemini_title": ia_service.gerar_titulos_com_gemini,
            "gemini_description": ia_service.gerar_descricao_com_gemini,
            "basic_title": basic_service.gerar_titulos_basicos,
            "basic_description": basic_service.gerar_descricao_basica,
        }
        try:
            return mapping[provider_key]
        except KeyError as exc:
            raise ValueError(f"Unsupported generation provider key: {provider_key}") from exc

    @staticmethod
    def build_fornecedor_import_job_service(
        *,
        session_provider: Any | None = None,
    ) -> Any:
        """Compose the import commit service used by background backends."""
        from Backend.application.services.fornecedor_import_job_service import (
            FornecedorImportJobService,
        )

        return FornecedorImportJobService(
            session_provider=session_provider or background_session_provider(),
            import_job_repository_factory=FornecedorImportJobRepository,
            produto_repository_factory=ProductRepository,
            produto_create_schema=schemas.ProdutoCreate,
        )

    @staticmethod
    def build_pdf_region_extractor() -> Callable[..., Any]:
        """Return the shared PDF region extraction callable."""
        service_container = ServiceContainer()
        return service_container.file_processing.extract_data_from_pdf_region


build_web_enrichment_task_runner = BackgroundRuntimeFactories.build_web_enrichment_task_runner
build_catalog_import_task_runner = BackgroundRuntimeFactories.build_catalog_import_task_runner
build_generation_task_service = BackgroundRuntimeFactories.build_generation_task_service
resolve_generation_callable = BackgroundRuntimeFactories.resolve_generation_callable
build_fornecedor_import_job_service = BackgroundRuntimeFactories.build_fornecedor_import_job_service
build_pdf_region_extractor = BackgroundRuntimeFactories.build_pdf_region_extractor
background_session_provider = BackgroundRuntimeFactories.background_session_provider
