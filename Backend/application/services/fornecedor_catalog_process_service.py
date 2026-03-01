from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

from Backend.application.services.repository_runtime_support import RepositoryRuntimeSupport


class FornecedorCatalogProcessService:
    """Encapsula validacoes e disparo do processamento completo de catalogo."""

    def __init__(
        self,
        *,
        models: Any,
        catalog_import_start_service: Any,
        fornecedor_repo: Any | None = None,
        catalog_file_repository: Any | None = None,
    ) -> None:
        if catalog_file_repository is None:
            catalog_file_repository = getattr(
                catalog_import_start_service,
                "_catalog_file_repository",
                None,
            )
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._fornecedor_repo = fornecedor_repo
        self._catalog_file_repository = catalog_file_repository
        self._catalog_import_start_service = catalog_import_start_service

    async def start_full_processing(
        self,
        *,
        background_tasks: Any,
        current_user: Any,
        file_id: int,
        fornecedor_id: int,
        tipo_produto_id: int,
        start_page: int,
        region: Optional[list[float]],
        mapping: Optional[Dict[str, str]],
        fornecedor_repo: Any | None = None,
        catalog_file_repo: Any | None = None,
        db_session_factory: Any | None = None,
    ) -> Dict[str, Any]:
        if fornecedor_repo is None:
            fornecedor_repo = self._fornecedor_repo
        if catalog_file_repo is None:
            catalog_file_repo = self._catalog_file_repository
        if db_session_factory is None:
            raise ValueError("db_session_factory is required")
        if fornecedor_repo is None:
            raise ValueError("fornecedor_repo is required")
        if catalog_file_repo is None:
            raise ValueError("catalog_file_repo is required")

        fornecedor = self._validate_fornecedor_access(
            fornecedor_repo=fornecedor_repo,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )
        source = self._catalog_import_start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=current_user.id,
            catalog_file_repo=catalog_file_repo,
        )
        pages = self._catalog_import_start_service.resolve_pdf_pages(
            catalog_file=source,
            start_page=start_page,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
            fornecedor_id=fornecedor.id,
            mapping=mapping,
            fornecedor_repo=fornecedor_repo,
        )
        job = self._create_processing_job_from_source(
            source=source,
            user_id=current_user.id,
            fornecedor_id=fornecedor.id,
            catalog_file_repo=catalog_file_repo,
        )
        command = self._catalog_import_start_service.build_finalize_command(
            file_id=job.id,
            user_id=current_user.id,
            product_type_id=tipo_produto_id,
            fornecedor_id=fornecedor.id,
            mapping=resolved_mapping,
            pages=pages,
            region=region,
        )
        if db_session_factory is not None:
            await self._catalog_import_start_service.dispatch_finalize(
                background_tasks=background_tasks,
                db_session_factory=db_session_factory,
                command=command,
            )
        return {"job_id": job.id, "status": "PROCESSING"}

    def _validate_fornecedor_access(
        self,
        *,
        fornecedor_repo: Any,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        fornecedor = RepositoryRuntimeSupport.call_repository_method(
            fornecedor_repo,
            "get_fornecedor",
            session=getattr(fornecedor_repo, "_db", None),
            fornecedor_id=fornecedor_id,
        )
        if not fornecedor:
            raise HTTPException(status_code=404, detail="Fornecedor nao encontrado")
        if not current_user.is_superuser and fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Nao autorizado")
        return fornecedor

    def _create_processing_job_from_source(
        self,
        *,
        source: Any,
        user_id: int,
        fornecedor_id: int,
        catalog_file_repo: Any,
    ) -> Any:
        job = self._models.CatalogImportFile(
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            original_filename=source.original_filename,
            stored_filename=source.stored_filename,
            status="PROCESSING",
        )
        RepositoryRuntimeSupport.call_repository_method(
            catalog_file_repo,
            "save_catalog_file",
            session=getattr(catalog_file_repo, "_db", None),
            catalog_file=job,
        )
        return job
