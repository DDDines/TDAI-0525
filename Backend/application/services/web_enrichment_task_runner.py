from __future__ import annotations

from typing import Any, Dict, Optional

from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskService,
)


class WebEnrichmentTaskRunner:
    """Orquestra instancia OOP do servico de task de enriquecimento."""

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
        legacy_web_extractor: Any | None = None,
        oop_web_extractor: Any | None = None,
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
        _ = (legacy_web_extractor, oop_web_extractor)
        self._web_extractor = web_extractor
        self._services: Dict[str, WebEnrichmentTaskService] = {}

    def _build(self, *, pipeline_variant: str = "oop") -> WebEnrichmentTaskService:
        _ = pipeline_variant
        build_kwargs = dict(self._kwargs)
        build_kwargs["web_extractor"] = self._web_extractor
        return WebEnrichmentTaskService(
            pipeline_variant="oop",
            **build_kwargs,
        )

    def _get_service(self, *, pipeline_variant: str = "oop") -> WebEnrichmentTaskService:
        service = self._services.get(pipeline_variant)
        if service is None:
            service = self._build(pipeline_variant=pipeline_variant)
            self._services[pipeline_variant] = service
        return service

    async def execute(
        self,
        *,
        db_session_factory: Any,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        await self._get_service(pipeline_variant="oop").execute(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

    async def execute_oop(self, **task_kwargs: Any) -> None:
        await self._get_service(pipeline_variant="oop").execute(**task_kwargs)

    async def execute_legacy(self, **task_kwargs: Any) -> None:
        await self._get_service(pipeline_variant="legacy").execute(**task_kwargs)

