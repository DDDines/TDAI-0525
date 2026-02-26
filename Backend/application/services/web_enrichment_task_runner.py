from __future__ import annotations

from typing import Any, Optional

from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskService,
)


class WebEnrichmentTaskRunner:
    """Orquestra instancias legacy/oop do servico de task de enriquecimento."""

    def __init__(
        self,
        *,
        logger: Any,
        SQLAlchemyError: Any,
        crud_users: Any,
        crud_produtos: Any,
        crud: Any,
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
    ) -> None:
        self._kwargs = {
            "logger": logger,
            "SQLAlchemyError": SQLAlchemyError,
            "crud_users": crud_users,
            "crud_produtos": crud_produtos,
            "crud": crud,
            "models": models,
            "schemas": schemas,
            "web_extractor": web_extractor,
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
        self._legacy_service: Optional[WebEnrichmentTaskService] = None
        self._oop_service: Optional[WebEnrichmentTaskService] = None

    def _build(self, *, pipeline_variant: str) -> WebEnrichmentTaskService:
        return WebEnrichmentTaskService(
            pipeline_variant=pipeline_variant,
            **self._kwargs,
        )

    def _get_service(self, variant: str) -> WebEnrichmentTaskService:
        if variant == "legacy":
            if self._legacy_service is None:
                self._legacy_service = self._build(pipeline_variant="legacy")
            return self._legacy_service
        if self._oop_service is None:
            self._oop_service = self._build(pipeline_variant="oop")
        return self._oop_service

    async def execute_legacy(
        self,
        *,
        db_session_factory: Any,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        await self._get_service("legacy").execute(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

    async def execute_oop(self, **task_kwargs: Any) -> None:
        await self._get_service("oop").execute(**task_kwargs)
