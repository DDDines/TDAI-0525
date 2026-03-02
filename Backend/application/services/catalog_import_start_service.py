"""Catalog import start service.

Defines the module responsibilities and how it fits in the backend architecture.
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
        """Initialize required dependencies and runtime configuration."""
        self._models = models
        self._fornecedor_repo = fornecedor_repo
        self._settings = settings
        self._resolve_storage_path = resolve_storage_path
        self._finalize_service = finalize_service
        self._catalog_file_repository = catalog_file_repository

    def _resolve_catalog_file_repo(
        self,
    ) -> Any:
        """Process Resolve catalog file repo."""
        return self._catalog_file_repository

    def _resolve_fornecedor_repo(
        self,
    ) -> Any:
        """Process Resolve fornecedor repo."""
        return self._fornecedor_repo

    def get_catalog_file_or_404(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Any:
        """Return Catalog file or 404."""
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
        """Resolve fornecedor id."""
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
        """Mark processing."""
        repo = self._resolve_catalog_file_repo()
        catalog_file.status = "PROCESSING"
        catalog_file.fornecedor_id = fornecedor_id
        if reset_pages:
            catalog_file.pages_processed = 0
            catalog_file.total_pages = 0
        repo.update_catalog_file(catalog_file=catalog_file)

    def ensure_catalog_binary_exists(self, *, catalog_file: Any) -> None:
        """Ensure catalog binary exists."""
        file_path = self._catalog_path(catalog_file)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    def resolve_pdf_pages(
        self,
        *,
        catalog_file: Any,
        start_page: int,
    ) -> list[int]:
        """Resolve pdf pages."""
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
        """Resolve mapping."""
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
    ) -> CatalogImportFinalizeCommand:
        """Build finalize command."""
        return CatalogImportFinalizeCommand(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )

    async def dispatch_finalize(
        self,
        *,
        background_tasks: Any,
        command: CatalogImportFinalizeCommand,
    ) -> Any:
        """Dispatch finalize."""
        return await self._finalize_service.dispatch_or_run(
            background_tasks=background_tasks,
            command=command,
        )

    async def run_finalize_direct(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> Any:
        """Run finalize direct."""
        return await self._finalize_service.run_direct(
            command=command,
        )

    def _catalog_path(self, catalog_file: Any) -> Path:
        """Process Catalog path."""
        return self._resolve_storage_path(
            Path(self._settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        )

    @staticmethod
    def _count_pdf_pages(content: bytes) -> int:
        """Process Count pdf pages."""
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return len(pdf.pages)
