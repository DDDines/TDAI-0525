"""Catalog import start service.

Contains cohesive services used by the catalog import pipeline.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand


class CatalogImportStartService:
    """Prepara e dispara o fluxo de finalizacao/reprocessamento da importacao."""

    def __init__(
        self,
        *,
        models: Any,
        settings: Any,
        resolve_storage_path: Any,
        finalize_service: Any,
        catalog_file_repository: Any,
        fornecedor_repo: Any,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Catalog Import Start Service."""
        self._models = models
        self._fornecedor_repo = fornecedor_repo
        self._settings = settings
        self._resolve_storage_path = resolve_storage_path
        self._finalize_service = finalize_service
        self._catalog_file_repository = catalog_file_repository

    def _resolve_catalog_file_repo(
        self,
    ) -> Any:
        """Handle resolve catalog file repo within the catalog import workflow."""
        return self._catalog_file_repository

    def _resolve_fornecedor_repo(
        self,
    ) -> Any:
        """Handle resolve fornecedor repo within the catalog import workflow."""
        return self._fornecedor_repo

    def get_catalog_file_or_404(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Any:
        """Retrieve catalog file or 404 using the current service dependencies."""
        repo = self._resolve_catalog_file_repo()
        catalog_file = repo.get_catalog_file_for_user(
            file_id=file_id,
            user_id=user_id,
        )
        if not catalog_file:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        return catalog_file

    def resolve_fornecedor_id(
        self,
        *,
        catalog_file: Any,
        fornecedor_id: Optional[int],
        required_message: str,
    ) -> int:
        """Resolve fornecedor id from injected repositories or runtime context."""
        fornecedor_id_final = fornecedor_id or catalog_file.fornecedor_id
        if not fornecedor_id_final:
            raise HTTPException(status_code=400, detail=required_message)
        return fornecedor_id_final

    def mark_processing(
        self,
        *,
        catalog_file: Any,
        fornecedor_id: int,
        reset_pages: bool = False,
    ) -> None:
        """Execute mark processing as part of this module workflow."""
        repo = self._resolve_catalog_file_repo()
        catalog_file.status = "PROCESSING"
        catalog_file.fornecedor_id = fornecedor_id
        if reset_pages:
            catalog_file.pages_processed = 0
            catalog_file.total_pages = 0
        repo.update_catalog_file(catalog_file=catalog_file)

    def ensure_catalog_binary_exists(self, *, catalog_file: Any) -> None:
        """Ensure catalog binary exists exists or is valid before continuing the flow."""
        file_path = self._catalog_path(catalog_file)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    def resolve_pdf_pages(
        self,
        *,
        catalog_file: Any,
        start_page: int,
    ) -> list[int]:
        """Resolve pdf pages from injected repositories or runtime context."""
        file_path = self._catalog_path(catalog_file)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        if file_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Formato de arquivo nao suportado")

        content = file_path.read_bytes()
        total_pages = self._count_pdf_pages(content)
        return list(range(start_page, total_pages + 1))

    def resolve_mapping(
        self,
        *,
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
    ) -> Optional[Dict[str, str]]:
        """Resolve mapping from injected repositories or runtime context."""
        if mapping is not None:
            return mapping
        repo = self._resolve_fornecedor_repo()
        fornecedor = repo.get_fornecedor(fornecedor_id=fornecedor_id)
        if fornecedor and fornecedor.default_column_mapping:
            return fornecedor.default_column_mapping
        return mapping

    @staticmethod
    def build_finalize_command(
        *,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[list[int]],
        region: Optional[list[float]],
        extraction_mode: str = "ocr",
    ) -> CatalogImportFinalizeCommand:
        """Build finalize command from current inputs and configuration."""
        return CatalogImportFinalizeCommand(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            extraction_mode=extraction_mode,
        )

    async def dispatch_finalize(
        self,
        *,
        background_tasks: Any,
        command: CatalogImportFinalizeCommand,
    ) -> Any:
        """Execute dispatch finalize as part of this module workflow."""
        return await self._finalize_service.dispatch_or_run(
            background_tasks=background_tasks,
            command=command,
        )

    async def run_finalize_direct(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> Any:
        """Execute run finalize direct as part of this module workflow."""
        return await self._finalize_service.run_direct(
            command=command,
        )

    def _catalog_path(self, catalog_file: Any) -> Path:
        """Handle catalog path within the catalog import workflow."""
        return self._resolve_storage_path(
            Path(self._settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        )

    @staticmethod
    def _count_pdf_pages(content: bytes) -> int:
        """Handle count pdf pages within the catalog import workflow."""
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return len(pdf.pages)
