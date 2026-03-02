"""Module fornecedor catalog process service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException


class FornecedorCatalogProcessService:
    """Encapsula validacoes e disparo do processamento completo de catalogo."""

    def __init__(
        self,
        *,
        models: Any,
        catalog_import_start_service: Any,
        fornecedor_repo: Any,
        catalog_file_repository: Any,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
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
    ) -> Dict[str, Any]:
        """Execute start_full_processing.

        This callable is documented to make behavior explicit for readers.
        """
        fornecedor = self._validate_fornecedor_access(
            fornecedor_repo=self._fornecedor_repo,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )
        source = self._catalog_import_start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=current_user.id,
        )
        pages = self._catalog_import_start_service.resolve_pdf_pages(
            catalog_file=source,
            start_page=start_page,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
            fornecedor_id=fornecedor.id,
            mapping=mapping,
        )
        job = self._create_processing_job_from_source(
            source=source,
            user_id=current_user.id,
            fornecedor_id=fornecedor.id,
            catalog_file_repo=self._catalog_file_repository,
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
        await self._catalog_import_start_service.dispatch_finalize(
            background_tasks=background_tasks,
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
        """Execute _validate_fornecedor_access.

        This callable is documented to make behavior explicit for readers.
        """
        fornecedor = fornecedor_repo.get_fornecedor(fornecedor_id=fornecedor_id)
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
        """Execute _create_processing_job_from_source.

        This callable is documented to make behavior explicit for readers.
        """
        job = self._models.CatalogImportFile(
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            original_filename=source.original_filename,
            stored_filename=source.stored_filename,
            status="PROCESSING",
        )
        catalog_file_repo.save_catalog_file(catalog_file=job)
        return job
