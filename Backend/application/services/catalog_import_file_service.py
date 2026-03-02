"""Module catalog import file service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

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
        catalog_file_repository: Any,
        fornecedor_repository: Any,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._models = models
        self._file_processing_service = file_processing_service
        self._catalog_import_start_service = catalog_import_start_service
        self._catalog_file_repository = catalog_file_repository
        self._fornecedor_repository = fornecedor_repository

    def _resolve_catalog_file_repo(
        self,
    ) -> Any:
        """Execute _resolve_catalog_file_repo.

        This callable is documented to make behavior explicit for readers.
        """
        return self._catalog_file_repository

    def _resolve_fornecedor_repo(self) -> Any:
        """Execute _resolve_fornecedor_repo.

        This callable is documented to make behavior explicit for readers.
        """
        return self._fornecedor_repository

    def list_user_files(
        self,
        *,
        user_id: int,
        fornecedor_id: int | None,
        skip: int,
        limit: int,
    ) -> dict[str, Any]:
        """Execute list_user_files.

        This callable is documented to make behavior explicit for readers.
        """
        repo = self._resolve_catalog_file_repo()
        items, total_items = repo.list_catalog_files_for_user(
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
        file_id: int,
        user_id: int,
    ) -> Any:
        """Execute get_user_file_or_404.

        This callable is documented to make behavior explicit for readers.
        """
        repo = self._resolve_catalog_file_repo()
        record = repo.get_catalog_file_for_user(
            file_id=file_id,
            user_id=user_id,
        )
        if not record:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        return record

    def delete_user_file(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Any:
        """Execute delete_user_file.

        This callable is documented to make behavior explicit for readers.
        """
        repo = self._resolve_catalog_file_repo()
        record = self.get_user_file_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        self._file_processing_service.delete_catalog_file(record.stored_filename)
        repo.delete_catalog_file(catalog_file=record)
        return record

    async def reprocess_catalog_file(
        self,
        *,
        background_tasks: Any,
        file_id: int,
        user_id: int,
        product_type_id: int | None,
        fornecedor_id: int | None,
        mapping: dict[str, str] | None,
        pages: list[int] | None,
        region: list[float] | None,
    ) -> dict[str, Any]:
        """Execute reprocess_catalog_file.

        This callable is documented to make behavior explicit for readers.
        """
        catalog_file_repo = self._resolve_catalog_file_repo()
        fornecedor_repo = self._resolve_fornecedor_repo()
        catalog_file = self._catalog_import_start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=user_id,
        )
        fornecedor_id_final = self._catalog_import_start_service.resolve_fornecedor_id(
            catalog_file=catalog_file,
            fornecedor_id=fornecedor_id,
            required_message="fornecedor_id e obrigatorio para reprocessar este arquivo.",
        )
        self._catalog_import_start_service.mark_processing(
            catalog_file=catalog_file,
            fornecedor_id=fornecedor_id_final,
            reset_pages=True,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
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
            command=command,
        )
        return {"status": "PROCESSING", "file_id": file_id}
