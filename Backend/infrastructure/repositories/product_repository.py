"""Repositorio de infraestrutura orientado a objetos para 'product_repository'."""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, selectinload

from Backend import schemas
from Backend.core.config import settings
from Backend.models import (
    ProductType,
    Produto,
    StatusEnriquecimentoEnum,
    StatusGeracaoIAEnum,
)

logger = logging.getLogger(__name__)

class ProductRepository:
    """Repository OO de Produto com Session vinculada por request."""
    _JSON_FIELDS: Tuple[str, ...] = (
        "dynamic_attributes",
        "dados_brutos_web",
        "log_enriquecimento_web",
    )

    def __init__(self, db: Session) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._db = db

    @staticmethod
    def _normalize_identifier_fields(produto_data: Dict[str, Any]) -> None:
        """Run normalize identifier fields in this workflow."""
        for field_name in ("sku", "ean"):
            if field_name in produto_data and produto_data[field_name] == "":
                produto_data[field_name] = None

    @staticmethod
    def _parse_json_fields(produto_data: Dict[str, Any], fields: List[str]) -> None:
        """Run parse json fields in this workflow."""
        for field_name in fields:
            if field_name in produto_data and isinstance(produto_data[field_name], str):
                try:
                    produto_data[field_name] = json.loads(produto_data[field_name])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{field_name} nao e um JSON string valido.") from exc

    @staticmethod
    def _apply_search_filter(query, search: Optional[str]):
        """Run apply search filter in this workflow."""
        if not search:
            return query

        search_term = f"%{search.lower()}%"
        return query.filter(
            or_(
                func.lower(Produto.nome_base).ilike(search_term),
                func.lower(Produto.nome_chat_api).ilike(search_term),
                func.lower(Produto.descricao_original).ilike(search_term),
                func.lower(Produto.descricao_chat_api).ilike(search_term),
                func.lower(Produto.sku).ilike(search_term),
                func.lower(Produto.ean).ilike(search_term),
                func.lower(Produto.marca).ilike(search_term),
                func.lower(Produto.modelo).ilike(search_term),
            )
        )

    @staticmethod
    def _apply_optional_filters(
        query,
        fornecedor_id: Optional[int],
        product_type_id: Optional[int],
        categoria: Optional[str],
        status_enriquecimento_web: Optional[StatusEnriquecimentoEnum],
        status_titulo_ia: Optional[StatusGeracaoIAEnum],
        status_descricao_ia: Optional[StatusGeracaoIAEnum],
    ):
        """Run apply optional filters in this workflow."""
        if fornecedor_id is not None:
            query = query.filter(Produto.fornecedor_id == fornecedor_id)
        if product_type_id is not None:
            query = query.filter(Produto.product_type_id == product_type_id)
        if categoria:
            query = query.filter(
                func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%")
            )
        if status_enriquecimento_web:
            query = query.filter(Produto.status_enriquecimento_web == status_enriquecimento_web)
        if status_titulo_ia:
            query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
        if status_descricao_ia:
            query = query.filter(Produto.status_descricao_ia == status_descricao_ia)
        return query

    @staticmethod
    def _apply_ordering(query, sort_by: Optional[str], sort_order: Optional[str]):
        """Run apply ordering in this workflow."""
        if sort_by:
            column_to_sort = getattr(Produto, sort_by, None)
            if column_to_sort is not None:
                if (sort_order or "asc").lower() == "desc":
                    return query.order_by(desc(column_to_sort))
                return query.order_by(asc(column_to_sort))
        return query.order_by(Produto.id)

    def _validate_unique_identifiers(self, *, user_id: int, produto_data: Dict[str, Any]) -> None:
        """Run validate unique identifiers in this workflow."""
        sku = produto_data.get("sku")
        ean = produto_data.get("ean")

        if sku:
            existing_sku = (
                self._db.query(Produto)
                .filter(Produto.user_id == user_id, Produto.sku == sku)
                .first()
            )
            if existing_sku:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um produto com o SKU '{sku}'.",
                )

        if ean:
            existing_ean = (
                self._db.query(Produto)
                .filter(Produto.user_id == user_id, Produto.ean == ean)
                .first()
            )
            if existing_ean:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um produto com o EAN '{ean}'.",
                )

    def create_produto(self, *, produto: schemas.ProdutoCreate, user_id: int) -> Produto:
        """Create produto for this workflow."""
        produto_data = produto.model_dump(exclude_unset=True)
        self._normalize_identifier_fields(produto_data)
        self._validate_unique_identifiers(user_id=user_id, produto_data=produto_data)
        self._parse_json_fields(produto_data, list(self._JSON_FIELDS))

        db_produto = Produto(**produto_data, user_id=user_id)
        self._db.add(db_produto)
        self._db.commit()
        self._db.refresh(db_produto)
        return db_produto

    def create_produtos_bulk(
        self,
        *,
        produtos: List[schemas.ProdutoCreate],
        user_id: int,
    ) -> Tuple[List[Produto], List[Produto], List[Dict[str, Any]]]:
        """Create produtos bulk for this workflow."""
        created_produtos: List[Produto] = []
        updated_produtos: List[Produto] = []
        erros: List[Dict[str, Any]] = []

        skus = [p.sku for p in produtos if p.sku]
        eans = [p.ean for p in produtos if p.ean]
        sku_map: Dict[str, Produto] = {}
        ean_map: Dict[str, Produto] = {}

        if skus or eans:
            existing = (
                self._db.query(Produto)
                .filter(Produto.user_id == user_id)
                .filter(or_(Produto.sku.in_(skus), Produto.ean.in_(eans)))
                .all()
            )
            for existing_produto in existing:
                if existing_produto.sku:
                    sku_map[existing_produto.sku] = existing_produto
                if existing_produto.ean:
                    ean_map[existing_produto.ean] = existing_produto

        new_skus: Set[str] = set()
        new_eans: Set[str] = set()

        for produto_schema in produtos:
            data = produto_schema.model_dump(exclude_unset=True)
            self._normalize_identifier_fields(data)
            self._parse_json_fields(data, list(self._JSON_FIELDS))

            sku = data.get("sku")
            ean = data.get("ean")

            if (sku and sku in new_skus) or (ean and ean in new_eans):
                erros.append(
                    {
                        "motivo_descarte": "Produto duplicado por SKU ou EAN",
                        "linha_original": data,
                        "duplicado": True,
                    }
                )
                continue

            existing_produto = None
            if sku and sku in sku_map:
                existing_produto = sku_map[sku]
            elif ean and ean in ean_map:
                existing_produto = ean_map[ean]

            if existing_produto:
                for key, value in data.items():
                    setattr(existing_produto, key, value)
                updated_produtos.append(existing_produto)
            else:
                db_produto = Produto(**data, user_id=user_id)
                self._db.add(db_produto)
                created_produtos.append(db_produto)

            if sku:
                new_skus.add(sku)
            if ean:
                new_eans.add(ean)

        self._db.commit()
        for produto_db in created_produtos + updated_produtos:
            self._db.refresh(produto_db)

        return created_produtos, updated_produtos, erros

    def get_produto(self, *, produto_id: int) -> Optional[Produto]:
        """Return produto for this workflow."""
        return (
            self._db.query(Produto)
            .options(
                selectinload(Produto.fornecedor),
                selectinload(Produto.product_type).selectinload(ProductType.attribute_templates),
            )
            .filter(Produto.id == produto_id)
            .first()
        )

    def get_produto_for_update(self, *, produto_id: int) -> Optional[Produto]:
        """Return produto for update for this workflow."""
        query = self._db.query(Produto).filter(Produto.id == produto_id)
        engine = self._db.get_bind()
        dialect_name = engine.dialect.name if engine and engine.dialect else None
        if dialect_name == "sqlite":
            return query.first()
        return query.with_for_update().first()

    def get_produtos_by_user(
        self,
        *,
        user_id: Optional[int],
        is_admin: bool,
        skip: int = 0,
        limit: int = 10,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "asc",
        search: Optional[str] = None,
        fornecedor_id: Optional[int] = None,
        product_type_id: Optional[int] = None,
        categoria: Optional[str] = None,
        status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None,
        status_titulo_ia: Optional[StatusGeracaoIAEnum] = None,
        status_descricao_ia: Optional[StatusGeracaoIAEnum] = None,
    ) -> List[Produto]:
        """Return produtos by user for this workflow."""
        query = self._db.query(Produto).options(
            selectinload(Produto.fornecedor),
            selectinload(Produto.product_type),
        )

        if not is_admin:
            if user_id is None:
                return []
            query = query.filter(Produto.user_id == user_id)

        query = self._apply_search_filter(query, search)
        query = self._apply_optional_filters(
            query=query,
            fornecedor_id=fornecedor_id,
            product_type_id=product_type_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
        )
        query = self._apply_ordering(query, sort_by, sort_order)
        return query.offset(skip).limit(limit).all()

    def count_produtos_by_user(
        self,
        *,
        user_id: Optional[int],
        is_admin: bool,
        search: Optional[str] = None,
        fornecedor_id: Optional[int] = None,
        product_type_id: Optional[int] = None,
        categoria: Optional[str] = None,
        status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None,
        status_titulo_ia: Optional[StatusGeracaoIAEnum] = None,
        status_descricao_ia: Optional[StatusGeracaoIAEnum] = None,
    ) -> int:
        """Count produtos by user for this workflow."""
        query = self._db.query(func.count(Produto.id))

        if not is_admin:
            if user_id is None:
                return 0
            query = query.filter(Produto.user_id == user_id)

        query = self._apply_search_filter(query, search)
        query = self._apply_optional_filters(
            query=query,
            fornecedor_id=fornecedor_id,
            product_type_id=product_type_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
        )

        count = query.scalar()
        return count if count is not None else 0

    def search_produtos_for_index(
        self,
        *,
        query_text: Optional[str],
        limit: int,
        user_id: Optional[int],
        is_admin: bool,
    ) -> List[Tuple[int, str, Any]]:
        """Return lightweight product rows for search endpoint rendering."""
        query = self._db.query(Produto.id, Produto.nome_base, Produto.created_at)
        if query_text:
            term = f"%{query_text.lower()}%"
            query = query.filter(func.lower(Produto.nome_base).ilike(term))
        if not is_admin:
            if user_id is None:
                return []
            query = query.filter(Produto.user_id == user_id)
        return query.order_by(Produto.created_at.desc()).limit(limit).all()

    def update_produto(
        self,
        *,
        db_produto: Produto,
        produto_update: schemas.ProdutoUpdate,
    ) -> Produto:
        """Update produto for this workflow."""
        update_data = produto_update.model_dump(exclude_unset=True)
        self._parse_json_fields(
            update_data,
            list(self._JSON_FIELDS) + ["imagens_secundarias_urls"],
        )

        for key, value in update_data.items():
            setattr(db_produto, key, value)

        self._db.commit()
        self._db.refresh(db_produto)
        self._db.refresh(db_produto, attribute_names=["fornecedor", "product_type"])
        if db_produto.product_type:
            self._db.refresh(db_produto.product_type, attribute_names=["attribute_templates"])
        return db_produto

    def delete_produto(self, *, db_produto: Produto) -> Produto:
        """Delete produto for this workflow."""
        self._db.delete(db_produto)
        self._db.commit()
        return db_produto

    async def save_produto_image(self, *, produto_id: int, file: UploadFile) -> str:
        """Run save produto image in this workflow."""
        _ = produto_id

        if not file.filename:
            raise ValueError("Nome do arquivo nao fornecido.")

        upload_dir = Path(settings.UPLOAD_DIRECTORY)
        if not upload_dir.is_absolute():
            upload_dir = Path(__file__).resolve().parents[2] / upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = upload_dir / unique_filename

        try:
            content = await file.read()
            with open(file_path, "wb") as output_file:
                output_file.write(content)
        except Exception as exc:
            raise IOError(f"Nao foi possivel salvar o arquivo: {exc}") from exc
        finally:
            await file.close()

        relative_path = Path(settings.UPLOAD_DIRECTORY) / unique_filename
        return f"/{relative_path.as_posix()}"

    def get_or_create_produto(self, *, produto: schemas.ProdutoCreate, user_id: int) -> Produto:
        """Return or create produto for this workflow."""
        base_query = self._db.query(Produto).filter(Produto.user_id == user_id)
        existing: Optional[Produto] = None

        if produto.sku:
            existing = base_query.filter(Produto.sku == produto.sku).first()
        elif produto.ean:
            existing = base_query.filter(Produto.ean == produto.ean).first()

        if existing:
            for key, value in produto.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            self._db.commit()
            self._db.refresh(existing)
            return existing

        return self.create_produto(produto=produto, user_id=user_id)
