import logging
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.models import CatalogImportFile, Fornecedor

logger = logging.getLogger(__name__)


def _normalize_supplier_url_fields(data: dict) -> None:
    if data.get("site_url") is not None:
        data["site_url"] = str(data["site_url"])
    if data.get("link_busca_padrao") is not None:
        data["link_busca_padrao"] = str(data["link_busca_padrao"])


def _validate_fornecedor_uniqueness(
    db: Session,
    user_id: int,
    fornecedor_data: dict,
) -> None:
    existing_fornecedor = (
        db.query(Fornecedor)
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
            db.query(Fornecedor)
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


def _apply_fornecedor_search_filter(query, search: Optional[str]):
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


class _FornecedorCrudWorkflow:
    def __init__(self, runtime: Optional["_FornecedorCrudRuntime"] = None) -> None:
        self._runtime = runtime or _FornecedorCrudRuntime()

    def create_fornecedor(
        self,
        db: Session,
        fornecedor: schemas.FornecedorCreate,
        user_id: int,
    ) -> Fornecedor:
        return self._runtime.create_fornecedor(db=db, fornecedor=fornecedor, user_id=user_id)

    def get_fornecedor(self, db: Session, fornecedor_id: int) -> Optional[Fornecedor]:
        return self._runtime.get_fornecedor(db=db, fornecedor_id=fornecedor_id)

    def get_fornecedores_by_user(
        self,
        db: Session,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[Fornecedor]:
        return self._runtime.get_fornecedores_by_user(
            db=db,
            user_id=user_id,
            is_admin=is_admin,
            skip=skip,
            limit=limit,
            search=search,
        )

    def count_fornecedores_by_user(
        self,
        db: Session,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        search: Optional[str] = None,
    ) -> int:
        return self._runtime.count_fornecedores_by_user(
            db=db,
            user_id=user_id,
            is_admin=is_admin,
            search=search,
        )

    def update_fornecedor(
        self,
        db: Session,
        db_fornecedor: Fornecedor,
        fornecedor_update: schemas.FornecedorUpdate,
    ) -> Fornecedor:
        return self._runtime.update_fornecedor(
            db=db,
            db_fornecedor=db_fornecedor,
            fornecedor_update=fornecedor_update,
        )

    def delete_fornecedor(self, db: Session, db_fornecedor: Fornecedor) -> Fornecedor:
        return self._runtime.delete_fornecedor(db=db, db_fornecedor=db_fornecedor)

    def create_catalog_import_file(
        self,
        db: Session,
        user_id: int,
        fornecedor_id: int,
        file_name: str,
        original_file_path: str,
    ) -> CatalogImportFile:
        return self._runtime.create_catalog_import_file(
            db=db,
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            file_name=file_name,
            original_file_path=original_file_path,
        )


class _FornecedorCrudRuntime:
    def create_fornecedor(
        self,
        db: Session,
        fornecedor: schemas.FornecedorCreate,
        user_id: int,
    ) -> Fornecedor:
        fornecedor_data = fornecedor.model_dump()
        _validate_fornecedor_uniqueness(
            db=db,
            user_id=user_id,
            fornecedor_data=fornecedor_data,
        )
        _normalize_supplier_url_fields(fornecedor_data)

        db_fornecedor = Fornecedor(**fornecedor_data, user_id=user_id)
        db.add(db_fornecedor)
        db.commit()
        db.refresh(db_fornecedor)
        return db_fornecedor

    def get_fornecedor(self, db: Session, fornecedor_id: int) -> Optional[Fornecedor]:
        return db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id).first()

    def get_fornecedores_by_user(
        self,
        db: Session,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[Fornecedor]:
        query = db.query(Fornecedor)
        if not is_admin and user_id:
            query = query.filter(Fornecedor.user_id == user_id)
        query = _apply_fornecedor_search_filter(query, search)
        return query.order_by(Fornecedor.nome).offset(skip).limit(limit).all()

    def count_fornecedores_by_user(
        self,
        db: Session,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        search: Optional[str] = None,
    ) -> int:
        query = db.query(func.count(Fornecedor.id))
        if not is_admin and user_id:
            query = query.filter(Fornecedor.user_id == user_id)
        query = _apply_fornecedor_search_filter(query, search)
        return query.scalar() or 0

    def update_fornecedor(
        self,
        db: Session,
        db_fornecedor: Fornecedor,
        fornecedor_update: schemas.FornecedorUpdate,
    ) -> Fornecedor:
        update_data = fornecedor_update.model_dump(exclude_unset=True)
        _normalize_supplier_url_fields(update_data)

        for key, value in update_data.items():
            setattr(db_fornecedor, key, value)
        db.commit()
        db.refresh(db_fornecedor)
        return db_fornecedor

    def delete_fornecedor(self, db: Session, db_fornecedor: Fornecedor) -> Fornecedor:
        db.delete(db_fornecedor)
        db.commit()
        return db_fornecedor

    def create_catalog_import_file(
        self,
        db: Session,
        user_id: int,
        fornecedor_id: int,
        file_name: str,
        original_file_path: str,
    ) -> CatalogImportFile:
        stored_filename = Path(original_file_path).name
        db_import_file = CatalogImportFile(
            original_filename=file_name,
            stored_filename=stored_filename,
            status="UPLOADED",
            fornecedor_id=fornecedor_id,
            user_id=user_id,
        )
        db.add(db_import_file)
        db.commit()
        db.refresh(db_import_file)
        return db_import_file


FornecedorCrudWorkflow = _FornecedorCrudWorkflow


def get_fornecedor_crud_workflow() -> FornecedorCrudWorkflow:
    return _FornecedorCrudWorkflow()

