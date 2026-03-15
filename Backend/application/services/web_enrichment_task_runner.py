"""Document web enrichment task runner module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Optional

from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskService,
)


class WebEnrichmentTaskRunner:
    """Orquestra instancia OOP do servico de task de enriquecimento."""

    def __init__(
        self,
        *,
        session_provider: Any,
        logger: Any,
        SQLAlchemyError: Any,
        models: Any,
        schemas: Any,
        web_extractor: Any,
        settings: Any,
        json_module: Any,
        re_module: Any,
        normalize_human_text: Any,
        build_payload_enriquecimento_visivel: Any,
        extrair_dominio_fornecedor: Any,
        priorizar_urls_para_enriquecimento: Any,
        is_meaningful_extracted_text: Any,
        metadata_has_minimum_signal: Any,
        is_source_relevant_for_product: Any,
        user_repository_factory: Any,
        product_repository_factory: Any,
        usage_repository_factory: Any,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Task Runner."""
        self._kwargs = {
            "session_provider": session_provider,
            "logger": logger,
            "SQLAlchemyError": SQLAlchemyError,
            "user_repository_factory": user_repository_factory,
            "product_repository_factory": product_repository_factory,
            "usage_repository_factory": usage_repository_factory,
            "models": models,
            "schemas": schemas,
            "settings": settings,
            "json": json_module,
            "re": re_module,
            "normalize_human_text": normalize_human_text,
            "build_payload_enriquecimento_visivel": build_payload_enriquecimento_visivel,
            "extrair_dominio_fornecedor": extrair_dominio_fornecedor,
            "priorizar_urls_para_enriquecimento": priorizar_urls_para_enriquecimento,
            "is_meaningful_extracted_text": is_meaningful_extracted_text,
            "metadata_has_minimum_signal": metadata_has_minimum_signal,
            "is_source_relevant_for_product": is_source_relevant_for_product,
        }
        self._web_extractor = web_extractor
        self._service: WebEnrichmentTaskService | None = None

    def _build(self) -> WebEnrichmentTaskService:
        """Execute build as part of this module workflow."""
        build_kwargs = dict(self._kwargs)
        build_kwargs["web_extractor"] = self._web_extractor
        return WebEnrichmentTaskService(**build_kwargs)

    def _get_service(self) -> WebEnrichmentTaskService:
        """Retrieve service using the current service dependencies."""
        if self._service is None:
            self._service = self._build()
        return self._service

    async def execute(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
        usar_ia: Optional[bool] = None,
    ) -> None:
        """Execute execute as part of this module workflow."""
        execute_kwargs = {
            "produto_id": produto_id,
            "user_id": user_id,
            "termos_busca_override": termos_busca_override,
        }
        if usar_ia is not None:
            execute_kwargs["usar_ia"] = usar_ia
        await self._get_service().execute(**execute_kwargs)

