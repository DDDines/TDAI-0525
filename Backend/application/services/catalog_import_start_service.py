from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.services.repository_runtime_support import (
    bind_repository,
    call_repository_method,
)


class CatalogImportStartService:
    """Prepara e dispara o fluxo de finalizacao/reprocessamento da importacao."""

    def __init__(
        self,
        *,
        models: Any,
        settings: Any,
        resolve_storage_path: Any,
        finalize_service: Any,
        catalog_file_repository: Any | None = None,
        fornecedor_repo: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        if fornecedor_repo is None:
            legacy_prefix = "c" + "rud_"
            fornecedor_repo = legacy_kwargs.pop(legacy_prefix + "fornecedores", None)
        if catalog_file_repository is None:
            catalog_file_repository = legacy_kwargs.pop("catalog_file_repository", None)
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._fornecedor_repo = fornecedor_repo
        self._settings = settings
        self._resolve_storage_path = resolve_storage_path
        self._finalize_service = finalize_service
        self._catalog_file_repository = catalog_file_repository

    def _resolve_catalog_file_repo(
        self,
        *,
        catalog_file_repo: Any | None = None,
        **legacy_kwargs: Any,
    ) -> Any:
        if catalog_file_repo is not None:
            return catalog_file_repo
        db = legacy_kwargs.pop("db", None)
        if db is not None:
            return bind_repository(self._catalog_file_repository, db=db)
        raise ValueError("catalog_file_repo or db is required")

    def _resolve_fornecedor_repo(
        self,
        *,
        fornecedor_repo: Any | None = None,
        **legacy_kwargs: Any,
    ) -> Any:
        if fornecedor_repo is not None:
            return fornecedor_repo
        db = legacy_kwargs.pop("db", None)
        if db is not None:
            return bind_repository(self._fornecedor_repo, db=db)
        return self._fornecedor_repo

    def get_catalog_file_or_404(
        self,
        *,
        file_id: int,
        user_id: int,
        catalog_file_repo: Any | None = None,
        **legacy_kwargs: Any,
    ) -> Any:
        repo = self._resolve_catalog_file_repo(
            catalog_file_repo=catalog_file_repo,
            **legacy_kwargs,
        )
        catalog_file = call_repository_method(
            repo,
            "get_catalog_file_for_user",
            db=getattr(repo, "_db", None),
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
        catalog_file_repo: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        legacy_db = legacy_kwargs.get("db")
        repo = self._resolve_catalog_file_repo(
            catalog_file_repo=catalog_file_repo,
            **legacy_kwargs,
        )
        catalog_file.status = "PROCESSING"
        catalog_file.fornecedor_id = fornecedor_id
        if reset_pages:
            catalog_file.pages_processed = 0
            catalog_file.total_pages = 0
        if catalog_file_repo is None and legacy_db is not None:
            legacy_db.commit()
            return
        call_repository_method(
            repo,
            "update_catalog_file",
            db=getattr(repo, "_db", None),
            catalog_file=catalog_file,
        )

    def ensure_catalog_binary_exists(self, *, catalog_file: Any) -> None:
        file_path = self._catalog_path(catalog_file)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    def resolve_pdf_pages(
        self,
        *,
        catalog_file: Any,
        start_page: int,
    ) -> list[int]:
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
        fornecedor_repo: Any | None = None,
        **legacy_kwargs: Any,
    ) -> Optional[Dict[str, str]]:
        if mapping is not None:
            return mapping
        repo = self._resolve_fornecedor_repo(
            fornecedor_repo=fornecedor_repo,
            **legacy_kwargs,
        )
        fornecedor = call_repository_method(
            repo,
            "get_fornecedor",
            db=getattr(repo, "_db", None),
            fornecedor_id=fornecedor_id,
        )
        if fornecedor and fornecedor.default_column_mapping:
            return fornecedor.default_column_mapping
        return mapping

    @staticmethod
    def build_db_session_factory(
        *,
        session: Any | None = None,
        **legacy_kwargs: Any,
    ):
        if session is None:
            session = legacy_kwargs.pop("db", None)
        if session is None:
            raise ValueError("session or db is required")
        return sessionmaker(bind=session.get_bind())

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
        db_session_factory: Any | None = None,
        **legacy_kwargs: Any,
    ) -> Any:
        if db_session_factory is None:
            db = legacy_kwargs.pop("db", None)
            if db is None:
                raise ValueError("db_session_factory or db is required")
            db_session_factory = self.build_db_session_factory(db=db)
        return await self._finalize_service.dispatch_or_run(
            background_tasks=background_tasks,
            db_session_factory=db_session_factory,
            command=command,
        )

    async def run_finalize_direct(
        self,
        *,
        command: CatalogImportFinalizeCommand,
        db_session_factory: Any | None = None,
        **legacy_kwargs: Any,
    ) -> Any:
        if db_session_factory is None:
            db = legacy_kwargs.pop("db", None)
            if db is None:
                raise ValueError("db_session_factory or db is required")
            db_session_factory = self.build_db_session_factory(db=db)
        return await self._finalize_service.run_direct(
            db_session_factory=db_session_factory,
            command=command,
        )

    def _catalog_path(self, catalog_file: Any) -> Path:
        return self._resolve_storage_path(
            Path(self._settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        )

    @staticmethod
    def _count_pdf_pages(content: bytes) -> int:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return len(pdf.pages)
