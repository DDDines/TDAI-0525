"""Module web enrichment task runner.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

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
        db_session_factory: Any,
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
        user_repository: Any,
        product_repository: Any,
        usage_repository: Any,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._kwargs = {
            "db_session_factory": db_session_factory,
            "logger": logger,
            "SQLAlchemyError": SQLAlchemyError,
            "user_repository": user_repository,
            "product_repository": product_repository,
            "usage_repository": usage_repository,
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
        """Execute _build.

        This callable is documented to make behavior explicit for readers.
        """
        build_kwargs = dict(self._kwargs)
        build_kwargs["web_extractor"] = self._web_extractor
        return WebEnrichmentTaskService(**build_kwargs)

    def _get_service(self) -> WebEnrichmentTaskService:
        """Execute _get_service.

        This callable is documented to make behavior explicit for readers.
        """
        if self._service is None:
            self._service = self._build()
        return self._service

    async def execute(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        """Execute execute.

        This callable is documented to make behavior explicit for readers.
        """
        await self._get_service().execute(
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

