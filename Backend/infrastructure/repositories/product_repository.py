"""Repositorio de infraestrutura orientado a objetos para 'product_repository'."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
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
from Backend.infrastructure.repositories.runtime_compatibility_repository import (
    ensure_attribute_templates_collect_in_ai,
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
        """Initialize injected dependencies and runtime configuration for Product Repository."""
        self._db = db
        ensure_attribute_templates_collect_in_ai(session=self._db)

    @staticmethod
    def _normalize_identifier_fields(produto_data: Dict[str, Any]) -> None:
        """Normalize identifier fields to keep behavior consistent across callers."""
        for field_name in ("sku", "ean"):
            if field_name in produto_data and produto_data[field_name] == "":
                produto_data[field_name] = None

    @staticmethod
    def _parse_json_fields(produto_data: Dict[str, Any], fields: List[str]) -> None:
        """Parse json fields into structured data used by downstream logic."""
        for field_name in fields:
            if field_name in produto_data and isinstance(produto_data[field_name], str):
                try:
                    produto_data[field_name] = json.loads(produto_data[field_name])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{field_name} nao e um JSON string valido.") from exc

    @staticmethod
    def _apply_active_filter(query):
        """Hide soft-deleted products from active read/list flows."""
        return query.filter(Produto.is_deleted.is_(False))

    @staticmethod
    def _apply_search_filter(query, search: Optional[str]):
        """Execute apply search filter as part of this module workflow."""
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
        enrichment_scope: Optional[str] = None,
    ):
        """Execute apply optional filters as part of this module workflow."""
        if fornecedor_id is not None:
            query = query.filter(Produto.fornecedor_id == fornecedor_id)
        if product_type_id is not None:
            query = query.filter(Produto.product_type_id == product_type_id)
        if categoria:
            query = query.filter(
                func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%")
            )
        if status_enriquecimento_web:
            if status_enriquecimento_web == StatusEnriquecimentoEnum.FALHA:
                query = query.filter(
                    Produto.status_enriquecimento_web.in_(
                        ProductRepository._failed_enrichment_statuses()
                    )
                )
            else:
                query = query.filter(Produto.status_enriquecimento_web == status_enriquecimento_web)
        if status_titulo_ia:
            query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
        if status_descricao_ia:
            query = query.filter(Produto.status_descricao_ia == status_descricao_ia)
        query = ProductRepository._apply_enrichment_scope_filter(query, enrichment_scope)
        return query

    @staticmethod
    def _failed_enrichment_statuses() -> List[StatusEnriquecimentoEnum]:
        """Return the grouped failure states exposed as a single filter in the UI."""
        return [
            StatusEnriquecimentoEnum.FALHA,
            StatusEnriquecimentoEnum.FALHOU,
            StatusEnriquecimentoEnum.FALHA_API_EXTERNA,
            StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA,
            StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA,
        ]

    @staticmethod
    def _apply_enrichment_scope_filter(query, enrichment_scope: Optional[str]):
        """Apply grouped enrichment scope filters used by list and bulk-selection screens."""
        scope = str(enrichment_scope or "").strip().lower()
        if not scope or scope == "all":
            return query
        if scope == "enriched":
            return query.filter(
                Produto.status_enriquecimento_web.in_(
                    [
                        StatusEnriquecimentoEnum.CONCLUIDO,
                        StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO,
                        StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS,
                    ]
                )
            )
        if scope == "pending":
            return query.filter(
                Produto.status_enriquecimento_web.in_(
                    [
                        StatusEnriquecimentoEnum.NAO_INICIADO,
                        StatusEnriquecimentoEnum.PENDENTE,
                        StatusEnriquecimentoEnum.EM_PROGRESSO,
                    ]
                )
            )
        if scope == "failed":
            return query.filter(
                Produto.status_enriquecimento_web.in_(ProductRepository._failed_enrichment_statuses())
            )
        return query

    @staticmethod
    def _apply_ordering(query, sort_by: Optional[str], sort_order: Optional[str]):
        """Execute apply ordering as part of this module workflow."""
        if sort_by:
            column_to_sort = getattr(Produto, sort_by, None)
            if column_to_sort is not None:
                if (sort_order or "asc").lower() == "desc":
                    return query.order_by(desc(column_to_sort))
                return query.order_by(asc(column_to_sort))
        return query.order_by(Produto.id)

    def _validate_unique_identifiers(self, *, user_id: int, produto_data: Dict[str, Any]) -> None:
        """Execute validate unique identifiers as part of this module workflow."""
        sku = produto_data.get("sku")
        ean = produto_data.get("ean")

        if sku:
            existing_sku = (
                self._db.query(Produto)
                .filter(
                    Produto.user_id == user_id,
                    Produto.sku == sku,
                    Produto.is_deleted.is_(False),
                )
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
                .filter(
                    Produto.user_id == user_id,
                    Produto.ean == ean,
                    Produto.is_deleted.is_(False),
                )
                .first()
            )
            if existing_ean:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ja existe um produto com o EAN '{ean}'.",
                )

    def _find_deleted_produto_by_identity(
        self,
        *,
        user_id: int,
        sku: Optional[str],
        ean: Optional[str],
    ) -> Optional[Produto]:
        """Resolve a soft-deleted product that can be revived by SKU/EAN identity."""
        identity_filters = []
        if sku:
            identity_filters.append(Produto.sku == sku)
        if ean:
            identity_filters.append(Produto.ean == ean)
        if not identity_filters:
            return None
        return (
            self._db.query(Produto)
            .filter(
                Produto.user_id == user_id,
                Produto.is_deleted.is_(True),
                or_(*identity_filters),
            )
            .order_by(desc(Produto.deleted_at), desc(Produto.id))
            .first()
        )

    def _restore_deleted_produto(
        self,
        *,
        db_produto: Produto,
        produto_data: Dict[str, Any],
    ) -> Produto:
        """Revive a soft-deleted record instead of creating a duplicate row."""
        for key, value in produto_data.items():
            setattr(db_produto, key, value)
        db_produto.is_deleted = False
        db_produto.deleted_at = None
        self._db.commit()
        self._db.refresh(db_produto)
        return db_produto

    def create_produto(self, *, produto: schemas.ProdutoCreate, user_id: int) -> Produto:
        """Create produto and return the resulting payload or entity."""
        produto_data = produto.model_dump(exclude_unset=True)
        self._normalize_identifier_fields(produto_data)
        self._validate_unique_identifiers(user_id=user_id, produto_data=produto_data)
        self._parse_json_fields(produto_data, list(self._JSON_FIELDS))

        deleted_match = self._find_deleted_produto_by_identity(
            user_id=user_id,
            sku=produto_data.get("sku"),
            ean=produto_data.get("ean"),
        )
        if deleted_match is not None:
            return self._restore_deleted_produto(
                db_produto=deleted_match,
                produto_data=produto_data,
            )

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
        """Create produtos bulk and return the resulting payload or entity."""
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
            deleted_sku_map: Dict[str, Produto] = {}
            deleted_ean_map: Dict[str, Produto] = {}
            for existing_produto in existing:
                if existing_produto.is_deleted:
                    if existing_produto.sku:
                        deleted_sku_map[existing_produto.sku] = existing_produto
                    if existing_produto.ean:
                        deleted_ean_map[existing_produto.ean] = existing_produto
                else:
                    if existing_produto.sku:
                        sku_map[existing_produto.sku] = existing_produto
                    if existing_produto.ean:
                        ean_map[existing_produto.ean] = existing_produto
        else:
            deleted_sku_map = {}
            deleted_ean_map = {}

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
                deleted_produto = None
                if sku and sku in deleted_sku_map:
                    deleted_produto = deleted_sku_map[sku]
                elif ean and ean in deleted_ean_map:
                    deleted_produto = deleted_ean_map[ean]

                if deleted_produto:
                    for key, value in data.items():
                        setattr(deleted_produto, key, value)
                    deleted_produto.is_deleted = False
                    deleted_produto.deleted_at = None
                    updated_produtos.append(deleted_produto)
                    if deleted_produto.sku:
                        sku_map[deleted_produto.sku] = deleted_produto
                    if deleted_produto.ean:
                        ean_map[deleted_produto.ean] = deleted_produto
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

    def get_produto(self, *, produto_id: int, user_id: Optional[int] = None) -> Optional[Produto]:
        """Retrieve produto using the current service dependencies.

        When *user_id* is provided the result is filtered to that owner,
        preventing cross-user data access from public-facing endpoints.
        Pass ``user_id=None`` only from internal/admin contexts.
        """
        query = (
            self._db.query(Produto)
            .options(
                selectinload(Produto.fornecedor),
                selectinload(Produto.product_type).selectinload(ProductType.attribute_templates),
            )
            .filter(Produto.id == produto_id)
        )
        query = self._apply_active_filter(query)
        if user_id is not None:
            query = query.filter(Produto.user_id == user_id)
        return query.first()

    def get_produto_for_update(self, *, produto_id: int, user_id: Optional[int] = None) -> Optional[Produto]:
        """Retrieve produto for update using the current service dependencies.

        When *user_id* is provided the result is filtered to that owner.
        """
        query = self._db.query(Produto).filter(Produto.id == produto_id)
        query = self._apply_active_filter(query)
        if user_id is not None:
            query = query.filter(Produto.user_id == user_id)
        engine = self._db.get_bind()
        dialect_name = engine.dialect.name if engine and engine.dialect else None
        if dialect_name == "sqlite":
            return query.first()
        return query.with_for_update().first()

    def set_web_enrichment_status(
        self,
        *,
        produto_id: int,
        status: StatusEnriquecimentoEnum,
        log_message: Optional[str] = None,
    ) -> Optional[Produto]:
        """Persist web enrichment status updates for a product."""
        produto = self.get_produto(produto_id=produto_id)
        if produto is None:
            return None

        produto.status_enriquecimento_web = status
        if log_message:
            historico: List[str] = []
            if isinstance(produto.log_enriquecimento_web, dict):
                previous = produto.log_enriquecimento_web.get("historico_mensagens", [])
                if isinstance(previous, list):
                    historico = [str(item) for item in previous]
            historico.append(log_message)
            produto.log_enriquecimento_web = {"historico_mensagens": historico}

        self._db.commit()
        self._db.refresh(produto)
        return produto

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
        enrichment_scope: Optional[str] = None,
    ) -> List[Produto]:
        """Retrieve produtos by user using the current service dependencies."""
        query = self._db.query(Produto).options(
            selectinload(Produto.fornecedor),
            selectinload(Produto.product_type),
        )
        query = self._apply_active_filter(query)

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
            enrichment_scope=enrichment_scope,
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
        enrichment_scope: Optional[str] = None,
    ) -> int:
        """Execute count produtos by user as part of this module workflow."""
        query = self._db.query(func.count(Produto.id))
        query = self._apply_active_filter(query)

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
            enrichment_scope=enrichment_scope,
        )

        count = query.scalar()
        return count if count is not None else 0

    def list_produto_ids_by_user(
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
        enrichment_scope: Optional[str] = None,
    ) -> List[int]:
        """Return all product IDs for the current filtered result set."""
        query = self._db.query(Produto.id)
        query = self._apply_active_filter(query)
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
            enrichment_scope=enrichment_scope,
        )
        query = self._apply_ordering(query, "id", "asc")
        return [produto_id for (produto_id,) in query.all()]

    def get_produtos_for_export(
        self,
        *,
        user_id: Optional[int],
        is_admin: bool,
        ids: Optional[List[int]] = None,
        search: Optional[str] = None,
        fornecedor_id: Optional[int] = None,
        product_type_id: Optional[int] = None,
        categoria: Optional[str] = None,
        status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None,
        status_titulo_ia: Optional[StatusGeracaoIAEnum] = None,
        status_descricao_ia: Optional[StatusGeracaoIAEnum] = None,
        enrichment_scope: Optional[str] = None,
        max_rows: int = 10000,
    ) -> List[Produto]:
        """Fetch products for spreadsheet export — no pagination, optional ID filter."""
        query = self._db.query(Produto).options(
            selectinload(Produto.fornecedor),
            selectinload(Produto.product_type),
        )
        query = self._apply_active_filter(query)

        if not is_admin:
            if user_id is None:
                return []
            query = query.filter(Produto.user_id == user_id)

        if ids:
            query = query.filter(Produto.id.in_(ids))
        else:
            query = self._apply_search_filter(query, search)
            query = self._apply_optional_filters(
                query=query,
                fornecedor_id=fornecedor_id,
                product_type_id=product_type_id,
                categoria=categoria,
                status_enriquecimento_web=status_enriquecimento_web,
                status_titulo_ia=status_titulo_ia,
                status_descricao_ia=status_descricao_ia,
                enrichment_scope=enrichment_scope,
            )

        return query.order_by(Produto.id.asc()).limit(max_rows).all()

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
        query = self._apply_active_filter(query)
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
        """Update produto and persist the resulting state changes."""
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
        """Execute delete produto as part of this module workflow."""
        db_produto.is_deleted = True
        db_produto.deleted_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(db_produto)
        return db_produto

    async def save_produto_image(self, *, produto_id: int, file: UploadFile) -> str:
        """Execute save produto image as part of this module workflow."""
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
        """Retrieve or create produto using the current service dependencies."""
        base_query = (
            self._db.query(Produto)
            .filter(Produto.user_id == user_id, Produto.is_deleted.is_(False))
        )
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

        deleted_match = self._find_deleted_produto_by_identity(
            user_id=user_id,
            sku=produto.sku,
            ean=produto.ean,
        )
        if deleted_match is not None:
            produto_data = produto.model_dump(exclude_unset=True)
            self._normalize_identifier_fields(produto_data)
            self._parse_json_fields(produto_data, list(self._JSON_FIELDS))
            return self._restore_deleted_produto(
                db_produto=deleted_match,
                produto_data=produto_data,
            )

        return self.create_produto(produto=produto, user_id=user_id)
