from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from Backend.application.services.repository_runtime_support import RepositoryRuntimeSupport


class CatalogImportFileService:
    """Gerencia listagem, exclusao e reprocessamento de arquivos de catalogo."""

    def __init__(
        self,
        *,
        models: Any,
        file_processing_service: Any,
        catalog_import_start_service: Any,
        catalog_file_repository: Any | None = None,
    ) -> None:
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._file_processing_service = file_processing_service
        self._catalog_import_start_service = catalog_import_start_service
        self._catalog_file_repository = catalog_file_repository

    def _resolve_catalog_file_repo(
        self,
        *,
        catalog_file_repo: Any | None = None,
    ) -> Any:
        if catalog_file_repo is not None:
            return catalog_file_repo
        if self._catalog_file_repository is None:
            raise ValueError("catalog_file_repo is required")
        if isinstance(self._catalog_file_repository, type):
            raise ValueError("catalog_file_repo instance is required")
        return self._catalog_file_repository

    def list_user_files(
        self,
        *,
        catalog_file_repo: Any | None = None,
        user_id: int,
        fornecedor_id: int | None,
        skip: int,
        limit: int,
    ) -> dict[str, Any]:
        repo = self._resolve_catalog_file_repo(
            catalog_file_repo=catalog_file_repo,
        )
        items, total_items = RepositoryRuntimeSupport.call_repository_method(
            repo,
            "list_catalog_files_for_user",
            session=getattr(repo, "_db", None),
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
        catalog_file_repo: Any | None = None,
        file_id: int,
        user_id: int,
    ) -> Any:
        repo = self._resolve_catalog_file_repo(
            catalog_file_repo=catalog_file_repo,
        )
        record = RepositoryRuntimeSupport.call_repository_method(
            repo,
            "get_catalog_file_for_user",
            session=getattr(repo, "_db", None),
            file_id=file_id,
            user_id=user_id,
        )
        if not record:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        return record

    def delete_user_file(
        self,
        *,
        catalog_file_repo: Any | None = None,
        file_id: int,
        user_id: int,
    ) -> Any:
        repo = self._resolve_catalog_file_repo(
            catalog_file_repo=catalog_file_repo,
        )
        record = self.get_user_file_or_404(
            catalog_file_repo=repo,
            file_id=file_id,
            user_id=user_id,
        )
        self._file_processing_service.delete_catalog_file(record.stored_filename)
        RepositoryRuntimeSupport.call_repository_method(
            repo,
            "delete_catalog_file",
            session=getattr(repo, "_db", None),
            catalog_file=record,
        )
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
        catalog_file_repo: Any | None = None,
        fornecedor_repo: Any | None = None,
        db_session_factory: Any | None = None,
    ) -> dict[str, Any]:
        if catalog_file_repo is None:
            catalog_file_repo = self._resolve_catalog_file_repo()
        if fornecedor_repo is None:
            fornecedor_repo = getattr(self._catalog_import_start_service, "_fornecedor_repo", None)
        if fornecedor_repo is None:
            raise ValueError("fornecedor_repo is required")
        if db_session_factory is None:
            raise ValueError("db_session_factory is required")

        catalog_file = self._catalog_import_start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=user_id,
            catalog_file_repo=catalog_file_repo,
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
            catalog_file_repo=catalog_file_repo,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
            fornecedor_id=fornecedor_id_final,
            mapping=mapping,
            fornecedor_repo=fornecedor_repo,
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
            db_session_factory=db_session_factory,
        )
        return {"status": "PROCESSING", "file_id": file_id}
