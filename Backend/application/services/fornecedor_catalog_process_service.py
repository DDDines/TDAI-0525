from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException


class FornecedorCatalogProcessService:
    """Encapsula validacoes e disparo do processamento completo de catalogo."""

    def __init__(
        self,
        *,
        models: Any,
        crud_fornecedores: Any,
        catalog_import_start_service: Any,
    ) -> None:
        self._models = models
        self._crud_fornecedores = crud_fornecedores
        self._catalog_import_start_service = catalog_import_start_service

    async def start_full_processing(
        self,
        *,
        background_tasks: Any,
        db: Any,
        current_user: Any,
        file_id: int,
        fornecedor_id: int,
        tipo_produto_id: int,
        start_page: int,
        region: Optional[list[float]],
        mapping: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        fornecedor = self._validate_fornecedor_access(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )
        source = self._catalog_import_start_service.get_catalog_file_or_404(
            db=db,
            file_id=file_id,
            user_id=current_user.id,
        )
        pages = self._catalog_import_start_service.resolve_pdf_pages(
            catalog_file=source,
            start_page=start_page,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
            db=db,
            fornecedor_id=fornecedor.id,
            mapping=mapping,
        )
        job = self._create_processing_job_from_source(
            db=db,
            source=source,
            user_id=current_user.id,
            fornecedor_id=fornecedor.id,
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
            db=db,
            command=command,
        )
        return {"job_id": job.id, "status": "PROCESSING"}

    def _validate_fornecedor_access(
        self,
        *,
        db: Any,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        fornecedor = self._crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)
        if not fornecedor:
            raise HTTPException(status_code=404, detail="Fornecedor nao encontrado")
        if not current_user.is_superuser and fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Nao autorizado")
        return fornecedor

    def _create_processing_job_from_source(
        self,
        *,
        db: Any,
        source: Any,
        user_id: int,
        fornecedor_id: int,
    ) -> Any:
        job = self._models.CatalogImportFile(
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            original_filename=source.original_filename,
            stored_filename=source.stored_filename,
            status="PROCESSING",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
