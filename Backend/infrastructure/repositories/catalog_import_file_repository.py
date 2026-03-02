"""Catalog import file repository.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from Backend.models import CatalogImportFile


class CatalogImportFileRepository:
    """Repository OO de arquivos de importacao de catalogo por request."""

    def __init__(self, db: Session) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._db = db

    def list_catalog_files_for_user(
        self,
        *,
        user_id: int,
        fornecedor_id: Optional[int],
        skip: int,
        limit: int,
    ) -> Tuple[List[CatalogImportFile], int]:
        """List catalog files for user."""
        query = self._db.query(CatalogImportFile).filter(
            CatalogImportFile.user_id == user_id
        )
        if fornecedor_id is not None:
            query = query.filter(CatalogImportFile.fornecedor_id == fornecedor_id)

        total_items = query.count()
        items = (
            query.order_by(CatalogImportFile.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total_items

    def get_catalog_file_for_user(
        self,
        *,
        file_id: int,
        user_id: int,
    ) -> Optional[CatalogImportFile]:
        """Return Catalog file for user."""
        return (
            self._db.query(CatalogImportFile)
            .filter_by(id=file_id, user_id=user_id)
            .first()
        )

    def get_catalog_file(self, *, file_id: int) -> Optional[CatalogImportFile]:
        """Return Catalog file."""
        return self._db.query(CatalogImportFile).filter_by(id=file_id).first()

    def save_catalog_file(self, *, catalog_file: CatalogImportFile) -> CatalogImportFile:
        """Process Save catalog file."""
        self._db.add(catalog_file)
        self._db.commit()
        self._db.refresh(catalog_file)
        return catalog_file

    def update_catalog_file(self, *, catalog_file: CatalogImportFile) -> CatalogImportFile:
        """Update catalog file."""
        self._db.add(catalog_file)
        self._db.commit()
        self._db.refresh(catalog_file)
        return catalog_file

    def delete_catalog_file(self, *, catalog_file: CatalogImportFile) -> None:
        """Delete catalog file."""
        self._db.delete(catalog_file)
        self._db.commit()
