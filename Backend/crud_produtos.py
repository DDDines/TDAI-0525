import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, selectinload

from Backend import schemas
from Backend.core.deprecation import deprecated_legacy_service_proxy
from Backend.core.config import settings
from Backend.models import (
    ProductType,
    Produto,
    StatusEnriquecimentoEnum,
    StatusGeracaoIAEnum,
)

logger = logging.getLogger(__name__)


_JSON_FIELDS = (
    "dynamic_attributes",
    "dados_brutos_web",
    "log_enriquecimento_web",
)


def _normalize_identifier_fields(produto_data: Dict[str, Any]) -> None:
    for field_name in ("sku", "ean"):
        if field_name in produto_data and produto_data[field_name] == "":
            produto_data[field_name] = None


def _parse_json_fields(produto_data: Dict[str, Any], fields: List[str]) -> None:
    for field_name in fields:
        if field_name in produto_data and isinstance(produto_data[field_name], str):
            try:
                produto_data[field_name] = json.loads(produto_data[field_name])
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{field_name} nao e um JSON string valido."
                ) from exc


def _validate_unique_identifiers(
    db: Session,
    user_id: int,
    produto_data: Dict[str, Any],
) -> None:
    sku = produto_data.get("sku")
    ean = produto_data.get("ean")

    if sku:
        existing_sku = (
            db.query(Produto)
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
            db.query(Produto)
            .filter(Produto.user_id == user_id, Produto.ean == ean)
            .first()
        )
        if existing_ean:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ja existe um produto com o EAN '{ean}'.",
            )


def _apply_search_filter(query, search: Optional[str]):
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


def _apply_optional_filters(
    query,
    fornecedor_id: Optional[int],
    product_type_id: Optional[int],
    categoria: Optional[str],
    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum],
    status_titulo_ia: Optional[StatusGeracaoIAEnum],
    status_descricao_ia: Optional[StatusGeracaoIAEnum],
):
    if fornecedor_id is not None:
        query = query.filter(Produto.fornecedor_id == fornecedor_id)
    if product_type_id is not None:
        query = query.filter(Produto.product_type_id == product_type_id)
    if categoria:
        query = query.filter(
            func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%")
        )
    if status_enriquecimento_web:
        query = query.filter(
            Produto.status_enriquecimento_web == status_enriquecimento_web
        )
    if status_titulo_ia:
        query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(Produto.status_descricao_ia == status_descricao_ia)
    return query


def _apply_ordering(query, sort_by: Optional[str], sort_order: Optional[str]):
    if sort_by:
        column_to_sort = getattr(Produto, sort_by, None)
        if column_to_sort is not None:
            if (sort_order or "asc").lower() == "desc":
                return query.order_by(desc(column_to_sort))
            return query.order_by(asc(column_to_sort))
    return query.order_by(Produto.id)


class _ProdutoCrudWorkflow:
    def __init__(self, runtime: Optional["_ProdutoCrudRuntime"] = None) -> None:
        self._runtime = runtime or _ProdutoCrudRuntime()

    def create_produto(
        self,
        db: Session,
        produto: schemas.ProdutoCreate,
        user_id: int,
    ) -> Produto:
        return self._runtime.create_produto(db=db, produto=produto, user_id=user_id)

    def create_produtos_bulk(
        self,
        db: Session,
        produtos: List[schemas.ProdutoCreate],
        user_id: int,
    ) -> Tuple[List[Produto], List[Produto], List[Dict[str, Any]]]:
        return self._runtime.create_produtos_bulk(db=db, produtos=produtos, user_id=user_id)

    def get_produto(self, db: Session, produto_id: int) -> Optional[Produto]:
        return self._runtime.get_produto(db=db, produto_id=produto_id)

    def get_produtos_by_user(
        self,
        db: Session,
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
        return self._runtime.get_produtos_by_user(
            db=db,
            user_id=user_id,
            is_admin=is_admin,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            fornecedor_id=fornecedor_id,
            product_type_id=product_type_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
        )

    def count_produtos_by_user(
        self,
        db: Session,
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
        return self._runtime.count_produtos_by_user(
            db=db,
            user_id=user_id,
            is_admin=is_admin,
            search=search,
            fornecedor_id=fornecedor_id,
            product_type_id=product_type_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
        )

    def update_produto(
        self,
        db: Session,
        db_produto: Produto,
        produto_update: schemas.ProdutoUpdate,
    ) -> Produto:
        return self._runtime.update_produto(
            db=db,
            db_produto=db_produto,
            produto_update=produto_update,
        )

    def delete_produto(self, db: Session, db_produto: Produto) -> Produto:
        return self._runtime.delete_produto(db=db, db_produto=db_produto)

    async def save_produto_image(
        self,
        db: Session,
        produto_id: int,
        file: UploadFile,
    ) -> str:
        return await self._runtime.save_produto_image(
            db=db,
            produto_id=produto_id,
            file=file,
        )

    def get_or_create_produto(
        self,
        db: Session,
        produto: schemas.ProdutoCreate,
        user_id: int,
    ) -> Produto:
        return self._runtime.get_or_create_produto(db=db, produto=produto, user_id=user_id)


class _ProdutoCrudRuntime:
    def create_produto(
        self,
        db: Session,
        produto: schemas.ProdutoCreate,
        user_id: int,
    ) -> Produto:
        produto_data = produto.model_dump(exclude_unset=True)
        _normalize_identifier_fields(produto_data)
        _validate_unique_identifiers(db=db, user_id=user_id, produto_data=produto_data)
        _parse_json_fields(produto_data, list(_JSON_FIELDS))

        db_produto = Produto(**produto_data, user_id=user_id)
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        return db_produto

    def create_produtos_bulk(
        self,
        db: Session,
        produtos: List[schemas.ProdutoCreate],
        user_id: int,
    ) -> Tuple[List[Produto], List[Produto], List[Dict[str, Any]]]:
        created_produtos: List[Produto] = []
        updated_produtos: List[Produto] = []
        erros: List[Dict[str, Any]] = []

        skus = [p.sku for p in produtos if p.sku]
        eans = [p.ean for p in produtos if p.ean]
        sku_map: Dict[str, Produto] = {}
        ean_map: Dict[str, Produto] = {}

        if skus or eans:
            existing = (
                db.query(Produto)
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
            _normalize_identifier_fields(data)
            _parse_json_fields(data, list(_JSON_FIELDS))

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
                db.add(db_produto)
                created_produtos.append(db_produto)

            if sku:
                new_skus.add(sku)
            if ean:
                new_eans.add(ean)

        db.commit()
        for produto_db in created_produtos + updated_produtos:
            db.refresh(produto_db)

        return created_produtos, updated_produtos, erros

    def get_produto(self, db: Session, produto_id: int) -> Optional[Produto]:
        return (
            db.query(Produto)
            .options(
                selectinload(Produto.fornecedor),
                selectinload(Produto.product_type).selectinload(
                    ProductType.attribute_templates
                ),
            )
            .filter(Produto.id == produto_id)
            .first()
        )

    def get_produtos_by_user(
        self,
        db: Session,
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
        query = db.query(Produto).options(
            selectinload(Produto.fornecedor),
            selectinload(Produto.product_type),
        )

        if not is_admin:
            if user_id is None:
                return []
            query = query.filter(Produto.user_id == user_id)

        query = _apply_search_filter(query, search)
        query = _apply_optional_filters(
            query=query,
            fornecedor_id=fornecedor_id,
            product_type_id=product_type_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
        )
        query = _apply_ordering(query, sort_by, sort_order)
        return query.offset(skip).limit(limit).all()

    def count_produtos_by_user(
        self,
        db: Session,
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
        query = db.query(func.count(Produto.id))

        if not is_admin:
            if user_id is None:
                return 0
            query = query.filter(Produto.user_id == user_id)

        query = _apply_search_filter(query, search)
        query = _apply_optional_filters(
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

    def update_produto(
        self,
        db: Session,
        db_produto: Produto,
        produto_update: schemas.ProdutoUpdate,
    ) -> Produto:
        update_data = produto_update.model_dump(exclude_unset=True)
        _parse_json_fields(
            update_data,
            list(_JSON_FIELDS) + ["imagens_secundarias_urls"],
        )

        for key, value in update_data.items():
            setattr(db_produto, key, value)

        db.commit()
        db.refresh(db_produto)
        db.refresh(db_produto, attribute_names=["fornecedor", "product_type"])
        if db_produto.product_type:
            db.refresh(db_produto.product_type, attribute_names=["attribute_templates"])
        return db_produto

    def delete_produto(self, db: Session, db_produto: Produto) -> Produto:
        db.delete(db_produto)
        db.commit()
        return db_produto

    async def save_produto_image(
        self,
        db: Session,
        produto_id: int,
        file: UploadFile,
    ) -> str:
        _ = db
        _ = produto_id

        if not file.filename:
            raise ValueError("Nome do arquivo nao fornecido.")

        upload_dir = Path(settings.UPLOAD_DIRECTORY)
        if not upload_dir.is_absolute():
            upload_dir = Path(__file__).resolve().parent / upload_dir
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

    def get_or_create_produto(
        self,
        db: Session,
        produto: schemas.ProdutoCreate,
        user_id: int,
    ) -> Produto:
        base_query = db.query(Produto).filter(Produto.user_id == user_id)
        existing: Optional[Produto] = None

        if produto.sku:
            existing = base_query.filter(Produto.sku == produto.sku).first()
        elif produto.ean:
            existing = base_query.filter(Produto.ean == produto.ean).first()

        if existing:
            for key, value in produto.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing

        return self.create_produto(db=db, produto=produto, user_id=user_id)


_produto_crud_workflow = _ProdutoCrudWorkflow()


def create_produto(
    db: Session,
    produto: schemas.ProdutoCreate,
    user_id: int,
) -> Produto:
    return _produto_crud_workflow.create_produto(db=db, produto=produto, user_id=user_id)


def create_produtos_bulk(
    db: Session,
    produtos: List[schemas.ProdutoCreate],
    user_id: int,
) -> Tuple[List[Produto], List[Produto], List[Dict[str, Any]]]:
    return _produto_crud_workflow.create_produtos_bulk(
        db=db,
        produtos=produtos,
        user_id=user_id,
    )


def get_produto(db: Session, produto_id: int) -> Optional[Produto]:
    return _produto_crud_workflow.get_produto(db=db, produto_id=produto_id)


def get_produtos_by_user(
    db: Session,
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
    return _produto_crud_workflow.get_produtos_by_user(
        db=db,
        user_id=user_id,
        is_admin=is_admin,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        fornecedor_id=fornecedor_id,
        product_type_id=product_type_id,
        categoria=categoria,
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
    )


def count_produtos_by_user(
    db: Session,
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
    return _produto_crud_workflow.count_produtos_by_user(
        db=db,
        user_id=user_id,
        is_admin=is_admin,
        search=search,
        fornecedor_id=fornecedor_id,
        product_type_id=product_type_id,
        categoria=categoria,
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
    )


def update_produto(
    db: Session,
    db_produto: Produto,
    produto_update: schemas.ProdutoUpdate,
) -> Produto:
    return _produto_crud_workflow.update_produto(
        db=db,
        db_produto=db_produto,
        produto_update=produto_update,
    )


def delete_produto(db: Session, db_produto: Produto) -> Produto:
    return _produto_crud_workflow.delete_produto(db=db, db_produto=db_produto)


async def save_produto_image(db: Session, produto_id: int, file: UploadFile) -> str:
    return await _produto_crud_workflow.save_produto_image(
        db=db,
        produto_id=produto_id,
        file=file,
    )


def get_or_create_produto(
    db: Session,
    produto: schemas.ProdutoCreate,
    user_id: int,
) -> Produto:
    return _produto_crud_workflow.get_or_create_produto(
        db=db,
        produto=produto,
        user_id=user_id,
    )


class ProdutoCrudLegacyService:
    def create_produto(self, *args, **kwargs):
        return create_produto(*args, **kwargs)

    def create_produtos_bulk(self, *args, **kwargs):
        return create_produtos_bulk(*args, **kwargs)

    def get_produto(self, *args, **kwargs):
        return get_produto(*args, **kwargs)

    def get_produtos_by_user(self, *args, **kwargs):
        return get_produtos_by_user(*args, **kwargs)

    def count_produtos_by_user(self, *args, **kwargs):
        return count_produtos_by_user(*args, **kwargs)

    def update_produto(self, *args, **kwargs):
        return update_produto(*args, **kwargs)

    def delete_produto(self, *args, **kwargs):
        return delete_produto(*args, **kwargs)

    async def save_produto_image(self, *args, **kwargs):
        return await save_produto_image(*args, **kwargs)

    def get_or_create_produto(self, *args, **kwargs):
        return get_or_create_produto(*args, **kwargs)


produto_crud_legacy_service = deprecated_legacy_service_proxy(
    ProdutoCrudLegacyService(),
    qualified_name="Backend.crud_produtos.produto_crud_legacy_service",
)
