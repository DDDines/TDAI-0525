from __future__ import annotations

from typing import Any, Dict, List, Optional

from Backend.application.services.catalog_import_task_service import (
    CatalogImportTaskService,
)


class CatalogImportTaskRunner:
    """Orquestra instancia OOP do servico de task de importacao."""

    def __init__(
        self,
        *,
        db_session_factory: Any,
        logger: Any,
        catalog_logger: Any,
        models: Any,
        schemas: Any,
        file_processing_service: Any,
        validator_crew: Any,
        settings: Any,
        path_cls: Any,
        time_module: Any,
        counter_cls: Any,
        resolve_storage_path: Any,
        normalize_import_issue_item: Any,
        extract_import_error_reason: Any,
        is_non_critical_import_reason: Any,
        normalizar_dados_validados: Any,
        sanitize_produto_extraido: Any,
        classificar_qualidade_linha_produto: Any,
        write_catalog_import_report: Any,
        normalize_import_text: Any,
        product_repository: Any,
        catalog_file_repository: Any,
    ) -> None:
        self._kwargs = {
            "db_session_factory": db_session_factory,
            "logger": logger,
            "catalog_logger": catalog_logger,
            "models": models,
            "schemas": schemas,
            "product_repository": product_repository,
            "catalog_file_repository": catalog_file_repository,
            "validator_crew": validator_crew,
            "settings": settings,
            "Path": path_cls,
            "time": time_module,
            "Counter": counter_cls,
            "resolve_storage_path": resolve_storage_path,
            "normalize_import_issue_item": normalize_import_issue_item,
            "extract_import_error_reason": extract_import_error_reason,
            "is_non_critical_import_reason": is_non_critical_import_reason,
            "normalizar_dados_validados": normalizar_dados_validados,
            "sanitize_produto_extraido": sanitize_produto_extraido,
            "classificar_qualidade_linha_produto": classificar_qualidade_linha_produto,
            "write_catalog_import_report": write_catalog_import_report,
            "normalize_import_text": normalize_import_text,
        }
        self._file_processing_service = file_processing_service
        self._service: CatalogImportTaskService | None = None

    def _build(self) -> CatalogImportTaskService:
        build_kwargs = dict(self._kwargs)
        build_kwargs["file_processing_service"] = self._file_processing_service
        return CatalogImportTaskService(**build_kwargs)

    def _get_service(self) -> CatalogImportTaskService:
        if self._service is None:
            self._service = self._build()
        return self._service

    async def execute(
        self,
        *,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> None:
        await self._get_service().execute(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )

