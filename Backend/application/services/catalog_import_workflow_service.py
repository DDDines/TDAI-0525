from __future__ import annotations

from typing import Any, Dict, List, Optional


class CatalogImportWorkflowService:
    """Orquestra finalizacao e leitura de status/resultados da importacao."""

    def __init__(
        self,
        *,
        start_service: Any,
        status_service: Any,
        runtime: Optional[Any] = None,
    ) -> None:
        if runtime is not None:
            start_service = getattr(runtime, "start_service", start_service)
            status_service = getattr(runtime, "status_service", status_service)
        self._start_service = start_service
        self._status_service = status_service

    async def importar_catalogo_finalizar(
        self,
        *,
        background_tasks: Any,
        file_id: int,
        product_type_id: int,
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
        user_id: int,
    ) -> Dict[str, Any]:
        catalog_file = self._start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        self._start_service.mark_processing(
            catalog_file=catalog_file,
            fornecedor_id=fornecedor_id,
            reset_pages=False,
        )
        self._start_service.ensure_catalog_binary_exists(catalog_file=catalog_file)
        resolved_mapping = self._start_service.resolve_mapping(
            fornecedor_id=fornecedor_id,
            mapping=mapping,
        )
        command = self._start_service.build_finalize_command(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=resolved_mapping,
            pages=pages,
            region=region,
        )
        await self._start_service.dispatch_finalize(
            background_tasks=background_tasks,
            command=command,
        )
        return {"status": "PROCESSING", "file_id": file_id}

    def importar_catalogo_status(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Any:
        return self._status_service.get_record_or_404(
            file_id=file_id,
            user_id=user_id,
        )

    def importar_catalogo_status_simple(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        record = self._status_service.get_record_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        return self._status_service.build_simple_status(record=record)

    def importar_catalogo_result(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Any:
        record = self._status_service.get_record_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        return self._status_service.build_result_response(record=record)

    async def importar_catalogo_finalizar_todas_paginas(
        self,
        *,
        file_id: int,
        start_page: int,
        mapping: Optional[Dict[str, str]],
        user_id: int,
    ) -> Any:
        record = self._start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        fornecedor_id_final = self._start_service.resolve_fornecedor_id(
            catalog_file=record,
            fornecedor_id=record.fornecedor_id,
            required_message="fornecedor_id e obrigatorio para processar este arquivo.",
        )
        pages = self._start_service.resolve_pdf_pages(
            catalog_file=record,
            start_page=start_page,
        )
        resolved_mapping = self._start_service.resolve_mapping(
            fornecedor_id=fornecedor_id_final,
            mapping=mapping,
        )
        command = self._start_service.build_finalize_command(
            file_id=file_id,
            user_id=user_id,
            product_type_id=None,
            fornecedor_id=fornecedor_id_final,
            mapping=resolved_mapping,
            pages=pages,
            region=None,
        )
        await self._start_service.run_finalize_direct(
            command=command,
        )
        refreshed_record = self._status_service.get_record_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        return refreshed_record.result_summary
