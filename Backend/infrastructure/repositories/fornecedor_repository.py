"""Repositorio de infraestrutura orientado a objetos para 'fornecedor_repository'."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.models import CatalogImportFile, Fornecedor
from Backend.infrastructure.repositories.runtime_compatibility_repository import (
    ensure_fornecedores_logo_url,
)


class FornecedorRepository:
    """Repository OO de Fornecedor com Session vinculada por request."""

    def __init__(self, db: Session) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedor Repository."""
        self._db = db
        ensure_fornecedores_logo_url(session=self._db)

    @staticmethod
    def _normalize_supplier_url_fields(data: dict) -> None:
        """Normalize supplier url fields to keep behavior consistent across callers."""
        if data.get("site_url") is not None:
            data["site_url"] = str(data["site_url"])
        if data.get("logo_url") is not None:
            data["logo_url"] = str(data["logo_url"])
        if data.get("link_busca_padrao") is not None:
            data["link_busca_padrao"] = str(data["link_busca_padrao"])

    @staticmethod
    def _apply_fornecedor_search_filter(query, search: Optional[str]):
        """Execute apply fornecedor search filter as part of this module workflow."""
        if not search:
            return query

        search_term = f"%{search.lower()}%"
        return query.filter(
            or_(
                func.lower(Fornecedor.nome).ilike(search_term),
                func.lower(Fornecedor.email_contato).ilike(search_term),
                func.lower(Fornecedor.contato_principal).ilike(search_term),
            )
        )

    def _validate_fornecedor_uniqueness(self, *, user_id: int, fornecedor_data: dict) -> None:
        """Execute validate fornecedor uniqueness as part of this module workflow."""
        existing_fornecedor = (
            self._db.query(Fornecedor)
            .filter(
                Fornecedor.user_id == user_id,
                func.lower(Fornecedor.nome) == func.lower(fornecedor_data["nome"]),
            )
            .first()
        )
        if existing_fornecedor:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ja existe um fornecedor com o nome '{fornecedor_data['nome']}'.",
            )

    def create_fornecedor(self, *, fornecedor: schemas.FornecedorCreate, user_id: int) -> Fornecedor:
        """Create fornecedor and return the resulting payload or entity."""
        fornecedor_data = fornecedor.model_dump()
        self._validate_fornecedor_uniqueness(user_id=user_id, fornecedor_data=fornecedor_data)
        self._normalize_supplier_url_fields(fornecedor_data)

        db_fornecedor = Fornecedor(**fornecedor_data, user_id=user_id)
        self._db.add(db_fornecedor)
        self._db.commit()
        self._db.refresh(db_fornecedor)
        return db_fornecedor

    def get_fornecedor(self, *, fornecedor_id: int, user_id: Optional[int] = None) -> Optional[Fornecedor]:
        """Retrieve fornecedor using the current service dependencies.

        When *user_id* is provided the result is filtered to that owner,
        preventing cross-user data access from public-facing endpoints.
        Pass ``user_id=None`` only from internal/admin contexts.
        """
        query = self._db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id)
        if user_id is not None:
            query = query.filter(Fornecedor.user_id == user_id)
        return query.first()

    def get_fornecedores_by_user(
        self,
        *,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[Fornecedor]:
        """Retrieve fornecedores by user using the current service dependencies."""
        query = self._db.query(Fornecedor)
        if not is_admin and user_id:
            query = query.filter(Fornecedor.user_id == user_id)
        query = self._apply_fornecedor_search_filter(query, search)
        return query.order_by(Fornecedor.nome).offset(skip).limit(limit).all()

    def count_fornecedores_by_user(
        self,
        *,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        search: Optional[str] = None,
    ) -> int:
        """Execute count fornecedores by user as part of this module workflow."""
        query = self._db.query(func.count(Fornecedor.id))
        if not is_admin and user_id:
            query = query.filter(Fornecedor.user_id == user_id)
        query = self._apply_fornecedor_search_filter(query, search)
        return query.scalar() or 0

    def list_fornecedor_ids_by_user(
        self,
        *,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        search: Optional[str] = None,
    ) -> List[int]:
        """Return all supplier IDs for the current filtered result set."""
        query = self._db.query(Fornecedor.id)
        if not is_admin and user_id:
            query = query.filter(Fornecedor.user_id == user_id)
        query = self._apply_fornecedor_search_filter(query, search)
        return [fornecedor_id for (fornecedor_id,) in query.order_by(Fornecedor.nome.asc()).all()]

    def search_fornecedores_for_index(
        self,
        *,
        query_text: Optional[str],
        limit: int,
        user_id: Optional[int],
        is_admin: bool,
    ):
        """Return lightweight supplier rows for search endpoint rendering."""
        query = self._db.query(Fornecedor.id, Fornecedor.nome, Fornecedor.created_at)
        if query_text:
            term = f"%{query_text.lower()}%"
            query = query.filter(func.lower(Fornecedor.nome).ilike(term))
        if not is_admin:
            if user_id is None:
                return []
            query = query.filter(Fornecedor.user_id == user_id)
        return query.order_by(Fornecedor.created_at.desc()).limit(limit).all()

    def update_fornecedor(
        self,
        *,
        db_fornecedor: Fornecedor,
        fornecedor_update: schemas.FornecedorUpdate,
    ) -> Fornecedor:
        """Update fornecedor and persist the resulting state changes."""
        update_data = fornecedor_update.model_dump(exclude_unset=True)
        self._normalize_supplier_url_fields(update_data)

        for key, value in update_data.items():
            setattr(db_fornecedor, key, value)
        self._db.commit()
        self._db.refresh(db_fornecedor)
        return db_fornecedor

    def exists_fornecedor_with_name_for_user(
        self,
        *,
        user_id: int,
        nome: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Exists fornecedor with name for user."""
        query = self._db.query(Fornecedor).filter(
            Fornecedor.user_id == user_id,
            func.lower(Fornecedor.nome) == func.lower(nome),
        )
        if exclude_id is not None:
            query = query.filter(Fornecedor.id != exclude_id)
        return query.first() is not None

    def set_default_column_mapping(
        self,
        *,
        db_fornecedor: Fornecedor,
        mapping: Optional[dict],
    ) -> Fornecedor:
        """Execute set default column mapping as part of this module workflow."""
        db_fornecedor.default_column_mapping = mapping
        self._db.add(db_fornecedor)
        self._db.commit()
        self._db.refresh(db_fornecedor)
        return db_fornecedor

    def delete_fornecedor(self, *, db_fornecedor: Fornecedor) -> Fornecedor:
        """Execute delete fornecedor as part of this module workflow."""
        self._db.delete(db_fornecedor)
        self._db.commit()
        return db_fornecedor

    def create_catalog_import_file(
        self,
        *,
        user_id: int,
        fornecedor_id: int,
        file_name: str,
        original_file_path: str,
    ) -> CatalogImportFile:
        """Create catalog import file and return the resulting payload or entity."""
        stored_filename = Path(original_file_path).name
        db_import_file = CatalogImportFile(
            original_filename=file_name,
            stored_filename=stored_filename,
            status="UPLOADED",
            fornecedor_id=fornecedor_id,
            user_id=user_id,
        )
        self._db.add(db_import_file)
        self._db.commit()
        self._db.refresh(db_import_file)
        return db_import_file
