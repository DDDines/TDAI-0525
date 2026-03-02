"""Repositorio de infraestrutura orientado a objetos para 'fornecedor_repository'."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.models import CatalogImportFile, Fornecedor


class FornecedorRepository:
    """Repository OO de Fornecedor com Session vinculada por request."""

    def __init__(self, db: Session) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._db = db

    @staticmethod
    def _normalize_supplier_url_fields(data: dict) -> None:
        """Execute _normalize_supplier_url_fields.

        This callable is documented to make behavior explicit for readers.
        """
        if data.get("site_url") is not None:
            data["site_url"] = str(data["site_url"])
        if data.get("link_busca_padrao") is not None:
            data["link_busca_padrao"] = str(data["link_busca_padrao"])

    @staticmethod
    def _apply_fornecedor_search_filter(query, search: Optional[str]):
        """Execute _apply_fornecedor_search_filter.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute _validate_fornecedor_uniqueness.

        This callable is documented to make behavior explicit for readers.
        """
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

        identificador_unico = fornecedor_data.get("identificador_unico")
        if identificador_unico:
            existing_identificador = (
                self._db.query(Fornecedor)
                .filter(
                    Fornecedor.user_id == user_id,
                    func.lower(Fornecedor.identificador_unico)
                    == func.lower(identificador_unico),
                )
                .first()
            )
            if existing_identificador:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Ja existe um fornecedor com o identificador unico "
                        f"'{identificador_unico}'."
                    ),
                )

    def create_fornecedor(self, *, fornecedor: schemas.FornecedorCreate, user_id: int) -> Fornecedor:
        """Execute create_fornecedor.

        This callable is documented to make behavior explicit for readers.
        """
        fornecedor_data = fornecedor.model_dump()
        self._validate_fornecedor_uniqueness(user_id=user_id, fornecedor_data=fornecedor_data)
        self._normalize_supplier_url_fields(fornecedor_data)

        db_fornecedor = Fornecedor(**fornecedor_data, user_id=user_id)
        self._db.add(db_fornecedor)
        self._db.commit()
        self._db.refresh(db_fornecedor)
        return db_fornecedor

    def get_fornecedor(self, *, fornecedor_id: int) -> Optional[Fornecedor]:
        """Execute get_fornecedor.

        This callable is documented to make behavior explicit for readers.
        """
        return self._db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id).first()

    def get_fornecedores_by_user(
        self,
        *,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[Fornecedor]:
        """Execute get_fornecedores_by_user.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute count_fornecedores_by_user.

        This callable is documented to make behavior explicit for readers.
        """
        query = self._db.query(func.count(Fornecedor.id))
        if not is_admin and user_id:
            query = query.filter(Fornecedor.user_id == user_id)
        query = self._apply_fornecedor_search_filter(query, search)
        return query.scalar() or 0

    def update_fornecedor(
        self,
        *,
        db_fornecedor: Fornecedor,
        fornecedor_update: schemas.FornecedorUpdate,
    ) -> Fornecedor:
        """Execute update_fornecedor.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute exists_fornecedor_with_name_for_user.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute set_default_column_mapping.

        This callable is documented to make behavior explicit for readers.
        """
        db_fornecedor.default_column_mapping = mapping
        self._db.add(db_fornecedor)
        self._db.commit()
        self._db.refresh(db_fornecedor)
        return db_fornecedor

    def delete_fornecedor(self, *, db_fornecedor: Fornecedor) -> Fornecedor:
        """Execute delete_fornecedor.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute create_catalog_import_file.

        This callable is documented to make behavior explicit for readers.
        """
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
