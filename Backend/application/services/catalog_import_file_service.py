from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from Backend.application.services.repository_runtime_support import (
    call_repository_method,
)


class CatalogImportFileService:
    """Gerencia listagem, exclusao e reprocessamento de arquivos de catalogo."""

    def __init__(
        self,
        *,
        models: Any,
        file_processing_service: Any,
        catalog_import_start_service: Any,
        catalog_file_repository: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        if catalog_file_repository is None:
            catalog_file_repository = legacy_kwargs.pop("catalog_file_repository", None)
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._file_processing_service = file_processing_service
        self._catalog_import_start_service = catalog_import_start_service
        self._catalog_file_repository = catalog_file_repository

    def list_user_files(
        self,
        *,
        db: Any,
        user_id: int,
        fornecedor_id: int | None,
        skip: int,
        limit: int,
    ) -> dict[str, Any]:
        items, total_items = call_repository_method(
            self._catalog_file_repository,
            "list_catalog_files_for_user",
            db=db,
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            skip=skip,
            limit=limit,
        )
        return {
            "items": items,
            "total_items": total_items,
            "page": skip // limit + 1,
            "limit": limit,
        }

    def get_user_file_or_404(
        self,
        *,
        db: Any,
        file_id: int,
        user_id: int,
    ) -> Any:
        record = call_repository_method(
            self._catalog_file_repository,
            "get_catalog_file_for_user",
            db=db,
            file_id=file_id,
            user_id=user_id,
        )
        if not record:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        return record

    def delete_user_file(
        self,
        *,
        db: Any,
        file_id: int,
        user_id: int,
    ) -> Any:
        record = self.get_user_file_or_404(db=db, file_id=file_id, user_id=user_id)
        self._file_processing_service.delete_catalog_file(record.stored_filename)
        call_repository_method(
            self._catalog_file_repository,
            "delete_catalog_file",
            db=db,
            catalog_file=record,
        )
        return record

    async def reprocess_catalog_file(
        self,
        *,
        background_tasks: Any,
        db: Any,
        file_id: int,
        user_id: int,
        product_type_id: int | None,
        fornecedor_id: int | None,
        mapping: dict[str, str] | None,
        pages: list[int] | None,
        region: list[float] | None,
    ) -> dict[str, Any]:
        catalog_file = self._catalog_import_start_service.get_catalog_file_or_404(
            db=db,
            file_id=file_id,
            user_id=user_id,
        )
        fornecedor_id_final = self._catalog_import_start_service.resolve_fornecedor_id(
            catalog_file=catalog_file,
            fornecedor_id=fornecedor_id,
            required_message="fornecedor_id e obrigatorio para reprocessar este arquivo.",
        )
        self._catalog_import_start_service.mark_processing(
            db=db,
            catalog_file=catalog_file,
            fornecedor_id=fornecedor_id_final,
            reset_pages=True,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
            db=db,
            fornecedor_id=fornecedor_id_final,
            mapping=mapping,
        )
        command = self._catalog_import_start_service.build_finalize_command(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id_final,
            mapping=resolved_mapping,
            pages=pages,
            region=region,
        )
        await self._catalog_import_start_service.dispatch_finalize(
            background_tasks=background_tasks,
            db=db,
            command=command,
        )
        return {"status": "PROCESSING", "file_id": file_id}
