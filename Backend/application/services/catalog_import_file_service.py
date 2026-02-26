from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class CatalogImportFileService:
    """Gerencia listagem, exclusao e reprocessamento de arquivos de catalogo."""

    def __init__(
        self,
        *,
        models: Any,
        file_processing_service: Any,
        catalog_import_start_service: Any,
    ) -> None:
        self._models = models
        self._file_processing_service = file_processing_service
        self._catalog_import_start_service = catalog_import_start_service

    def list_user_files(
        self,
        *,
        db: Any,
        user_id: int,
        fornecedor_id: int | None,
        skip: int,
        limit: int,
    ) -> dict[str, Any]:
        query = db.query(self._models.CatalogImportFile).filter(
            self._models.CatalogImportFile.user_id == user_id
        )
        if fornecedor_id is not None:
            query = query.filter(
                self._models.CatalogImportFile.fornecedor_id == fornecedor_id
            )
        total_items = query.count()
        items = (
            query.order_by(self._models.CatalogImportFile.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
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
        record = (
            db.query(self._models.CatalogImportFile)
            .filter_by(id=file_id, user_id=user_id)
            .first()
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
        db.delete(record)
        db.commit()
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
