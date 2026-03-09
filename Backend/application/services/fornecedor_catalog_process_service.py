"""Document fornecedor catalog process service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException


class FornecedorCatalogProcessService:
    """Encapsula validacoes e disparo do processamento completo de catalogo."""

    def __init__(
        self,
        *,
        catalog_import_start_service: Any,
        fornecedor_repo: Any,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedor Catalog Process Service."""
        self._fornecedor_repo = fornecedor_repo
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
        """Execute start full processing as part of this module workflow."""
        fornecedor = self._validate_fornecedor_access(
            fornecedor_repo=self._fornecedor_repo,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )
        source = self._catalog_import_start_service.get_catalog_file_or_404(
            file_id=file_id,
            user_id=current_user.id,
        )
        self._catalog_import_start_service.mark_processing(
            catalog_file=source,
            fornecedor_id=fornecedor.id,
            reset_pages=False,
        )
        self._catalog_import_start_service.ensure_catalog_binary_exists(
            catalog_file=source,
        )
        pages = self._catalog_import_start_service.resolve_pdf_pages(
            catalog_file=source,
            start_page=start_page,
        )
        resolved_mapping = self._catalog_import_start_service.resolve_mapping(
            fornecedor_id=fornecedor.id,
            mapping=mapping,
        )
        command = self._catalog_import_start_service.build_finalize_command(
            file_id=source.id,
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
        return {"job_id": source.id, "status": "PROCESSING"}

    def _validate_fornecedor_access(
        self,
        *,
        fornecedor_repo: Any,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        """Execute validate fornecedor access as part of this module workflow."""
        fornecedor = fornecedor_repo.get_fornecedor(fornecedor_id=fornecedor_id)
        if not fornecedor:
            raise HTTPException(status_code=404, detail="Fornecedor nao encontrado")
        if not current_user.is_superuser and fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Nao autorizado")
        return fornecedor

