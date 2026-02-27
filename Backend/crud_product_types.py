import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from Backend import schemas
from Backend.models import AttributeTemplate, ProductType, Produto

logger = logging.getLogger(__name__)


def _create_product_type_impl(
    db: Session,
    product_type_create: schemas.ProductTypeCreate,
    user_id: Optional[int] = None,
) -> ProductType:
    logger.debug(
        "CRUD(create_product_type): user_id=%s key_name=%s",
        user_id,
        product_type_create.key_name,
    )

    existing_query = db.query(ProductType).filter(
        func.lower(ProductType.key_name) == func.lower(product_type_create.key_name)
    )
    if user_id:
        existing_query = existing_query.filter(
            or_(ProductType.user_id == user_id, ProductType.user_id.is_(None))
        )
    else:
        existing_query = existing_query.filter(ProductType.user_id.is_(None))

    existing_product_type = existing_query.first()
    if existing_product_type:
        detail = (
            f"Ja existe um Tipo de Produto com a chave "
            f"'{product_type_create.key_name}'."
        )
        if existing_product_type.user_id is None:
            detail = (
                f"Um Tipo de Produto global com a chave "
                f"'{product_type_create.key_name}' ja existe e nao pode ser duplicado."
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    db_product_type = ProductType(
        key_name=product_type_create.key_name,
        friendly_name=product_type_create.friendly_name,
        description=getattr(product_type_create, "description", None),
        user_id=user_id,
    )
    db.add(db_product_type)
    db.flush()

    if (
        hasattr(product_type_create, "attribute_templates")
        and product_type_create.attribute_templates
    ):
        for attribute_data in product_type_create.attribute_templates:
            db_attribute = AttributeTemplate(
                **attribute_data.model_dump(),
                product_type_id=db_product_type.id,
            )
            db.add(db_attribute)

    db.commit()
    db.refresh(db_product_type)
    db.refresh(db_product_type, attribute_names=["attribute_templates"])
    logger.info(
        "CRUD(create_product_type): tipo '%s' (ID=%s) criado para user_id=%s",
        db_product_type.friendly_name,
        db_product_type.id,
        user_id,
    )
    return db_product_type


def _get_product_type_impl(
    db: Session,
    product_type_id: int,
) -> Optional[ProductType]:
    return (
        db.query(ProductType)
        .options(selectinload(ProductType.attribute_templates))
        .filter(ProductType.id == product_type_id)
        .first()
    )


def _get_product_type_by_key_name_impl(
    db: Session,
    key_name: str,
    user_id: Optional[int] = None,
) -> Optional[ProductType]:
    logger.debug(
        "CRUD(get_product_type_by_key_name): key_name=%s user_id=%s",
        key_name,
        user_id,
    )
    query = (
        db.query(ProductType)
        .options(selectinload(ProductType.attribute_templates))
        .filter(ProductType.key_name == key_name)
    )
    if user_id:
        product_type = (
            query.filter(or_(ProductType.user_id == user_id, ProductType.user_id.is_(None)))
            .order_by(ProductType.user_id.desc())
            .first()
        )
        if product_type:
            logger.debug(
                "CRUD: tipo encontrado (user/global): %s (ID=%s)",
                product_type.friendly_name,
                product_type.id,
            )
            return product_type
        logger.debug(
            "CRUD: nenhum tipo encontrado para key_name=%s user_id=%s",
            key_name,
            user_id,
        )
        return None

    product_type = query.filter(ProductType.user_id.is_(None)).first()
    if product_type:
        logger.debug(
            "CRUD: tipo global encontrado: %s (ID=%s)",
            product_type.friendly_name,
            product_type.id,
        )
        return product_type

    logger.debug("CRUD: nenhum tipo global encontrado para key_name=%s", key_name)
    return None


def _apply_product_type_search(query, search: Optional[str]):
    if not search:
        return query
    search_term = f"%{search.lower()}%"
    return query.filter(
        or_(
            func.lower(ProductType.key_name).ilike(search_term),
            func.lower(ProductType.friendly_name).ilike(search_term),
            func.lower(ProductType.description).ilike(search_term),
        )
    )


def _get_product_types_for_user_impl(
    db: Session,
    user_id: Optional[int],
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
) -> List[ProductType]:
    query = db.query(ProductType).options(selectinload(ProductType.attribute_templates))
    if user_id:
        query = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id.is_(None)))
    else:
        query = query.filter(ProductType.user_id.is_(None))

    query = _apply_product_type_search(query, search)
    return (
        query.order_by(ProductType.user_id.nullslast(), ProductType.friendly_name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def _count_product_types_for_user_impl(
    db: Session,
    user_id: Optional[int],
    search: Optional[str] = None,
) -> int:
    query = db.query(func.count(ProductType.id))
    if user_id:
        query = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id.is_(None)))
    else:
        query = query.filter(ProductType.user_id.is_(None))

    query = _apply_product_type_search(query, search)
    count = query.scalar()
    return count if count is not None else 0


def _update_product_type_impl(
    db: Session,
    db_product_type: ProductType,
    product_type_update: schemas.ProductTypeUpdate,
) -> ProductType:
    update_data = product_type_update.model_dump(exclude_unset=True)

    if "key_name" in update_data and update_data["key_name"] != db_product_type.key_name:
        existing_check = db.query(ProductType).filter(
            ProductType.key_name == update_data["key_name"],
            ProductType.id != db_product_type.id,
        )
        if db_product_type.user_id:
            existing_check = existing_check.filter(
                or_(
                    ProductType.user_id == db_product_type.user_id,
                    ProductType.user_id.is_(None),
                )
            )
        else:
            existing_check = existing_check.filter(ProductType.user_id.is_(None))

        if existing_check.first():
            raise IntegrityError(
                f"A chave '{update_data['key_name']}' ja esta em uso.",
                params={},
                orig=None,
            )

    for key, value in update_data.items():
        setattr(db_product_type, key, value)

    db.commit()
    db.refresh(db_product_type)
    db.refresh(db_product_type, attribute_names=["attribute_templates"])
    return db_product_type


def _delete_product_type_impl(db: Session, db_product_type: ProductType) -> ProductType:
    associated_products = (
        db.query(Produto).filter(Produto.product_type_id == db_product_type.id).count()
    )
    if associated_products > 0:
        raise IntegrityError(
            (
                f"Nao e possivel excluir o Tipo de Produto "
                f"'{db_product_type.friendly_name}' pois ele esta associado a "
                f"{associated_products} produto(s)."
            ),
            params={},
            orig=None,
        )

    db.delete(db_product_type)
    db.commit()
    return db_product_type


def _create_attribute_template_impl(
    db: Session,
    attr_template_create: schemas.AttributeTemplateCreate,
    product_type_id: int,
) -> AttributeTemplate:
    existing_attribute = (
        db.query(AttributeTemplate)
        .filter(
            AttributeTemplate.product_type_id == product_type_id,
            AttributeTemplate.attribute_key == attr_template_create.attribute_key,
        )
        .first()
    )
    if existing_attribute:
        raise IntegrityError(
            (
                f"O Tipo de Produto ID {product_type_id} ja possui um atributo com a "
                f"chave '{attr_template_create.attribute_key}'."
            ),
            params={},
            orig=None,
        )

    db_attr_template = AttributeTemplate(
        **attr_template_create.model_dump(),
        product_type_id=product_type_id,
    )
    db.add(db_attr_template)
    db.commit()
    db.refresh(db_attr_template)
    return db_attr_template


def _get_attribute_template_impl(
    db: Session,
    attribute_template_id: int,
) -> Optional[AttributeTemplate]:
    return (
        db.query(AttributeTemplate)
        .filter(AttributeTemplate.id == attribute_template_id)
        .first()
    )


def _update_attribute_template_impl(
    db: Session,
    db_attr_template: AttributeTemplate,
    attr_template_update: schemas.AttributeTemplateUpdate,
) -> AttributeTemplate:
    update_data = attr_template_update.model_dump(exclude_unset=True)

    if (
        "attribute_key" in update_data
        and update_data["attribute_key"] != db_attr_template.attribute_key
    ):
        existing_check = (
            db.query(AttributeTemplate)
            .filter(
                AttributeTemplate.product_type_id == db_attr_template.product_type_id,
                AttributeTemplate.attribute_key == update_data["attribute_key"],
                AttributeTemplate.id != db_attr_template.id,
            )
            .first()
        )
        if existing_check:
            raise IntegrityError(
                (
                    f"O Tipo de Produto ID {db_attr_template.product_type_id} ja possui "
                    f"um atributo com a chave '{update_data['attribute_key']}'."
                ),
                params={},
                orig=None,
            )

    for key, value in update_data.items():
        setattr(db_attr_template, key, value)
    db.commit()
    db.refresh(db_attr_template)
    return db_attr_template


def _delete_attribute_template_impl(
    db: Session,
    db_attr_template: AttributeTemplate,
) -> AttributeTemplate:
    db.delete(db_attr_template)
    db.commit()
    return db_attr_template


def _reorder_attribute_template_impl(
    db: Session,
    attribute_id: int,
    direction: str,
) -> Optional[AttributeTemplate]:
    attr_to_move = _get_attribute_template_impl(db=db, attribute_template_id=attribute_id)
    if not attr_to_move:
        return None

    siblings = (
        db.query(AttributeTemplate)
        .filter(AttributeTemplate.product_type_id == attr_to_move.product_type_id)
        .order_by(AttributeTemplate.display_order.asc(), AttributeTemplate.id.asc())
        .all()
    )

    if any(sibling.display_order is None for sibling in siblings):
        for index, sibling in enumerate(siblings):
            sibling.display_order = index
        db.commit()
        db.refresh(attr_to_move)

    try:
        current_index = siblings.index(attr_to_move)
    except ValueError:
        return None

    if direction == "up" and current_index > 0:
        previous_item = siblings[current_index - 1]
        previous_item.display_order, attr_to_move.display_order = (
            attr_to_move.display_order,
            previous_item.display_order,
        )
        db.commit()
    elif direction == "down" and current_index < len(siblings) - 1:
        next_item = siblings[current_index + 1]
        next_item.display_order, attr_to_move.display_order = (
            attr_to_move.display_order,
            next_item.display_order,
        )
        db.commit()

    siblings_reordered = (
        db.query(AttributeTemplate)
        .filter(AttributeTemplate.product_type_id == attr_to_move.product_type_id)
        .order_by(AttributeTemplate.display_order.asc(), AttributeTemplate.id.asc())
        .all()
    )
    for index, sibling in enumerate(siblings_reordered):
        sibling.display_order = index

    db.commit()
    db.refresh(attr_to_move)
    return attr_to_move


class _ProductTypeCrudWorkflow:
    def __init__(self, runtime: Optional["_ProductTypeCrudRuntime"] = None) -> None:
        self._runtime = runtime or _ProductTypeCrudRuntime()

    def create_product_type(
        self,
        db: Session,
        product_type_create: schemas.ProductTypeCreate,
        user_id: Optional[int] = None,
    ) -> ProductType:
        return self._runtime.create_product_type(
            db=db,
            product_type_create=product_type_create,
            user_id=user_id,
        )

    def get_product_type(self, db: Session, product_type_id: int) -> Optional[ProductType]:
        return self._runtime.get_product_type(db=db, product_type_id=product_type_id)

    def get_product_type_by_key_name(
        self,
        db: Session,
        key_name: str,
        user_id: Optional[int] = None,
    ) -> Optional[ProductType]:
        return self._runtime.get_product_type_by_key_name(
            db=db,
            key_name=key_name,
            user_id=user_id,
        )

    def get_product_types_for_user(
        self,
        db: Session,
        user_id: Optional[int],
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[ProductType]:
        return self._runtime.get_product_types_for_user(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            search=search,
        )

    def count_product_types_for_user(
        self,
        db: Session,
        user_id: Optional[int],
        search: Optional[str] = None,
    ) -> int:
        return self._runtime.count_product_types_for_user(
            db=db,
            user_id=user_id,
            search=search,
        )

    def update_product_type(
        self,
        db: Session,
        db_product_type: ProductType,
        product_type_update: schemas.ProductTypeUpdate,
    ) -> ProductType:
        return self._runtime.update_product_type(
            db=db,
            db_product_type=db_product_type,
            product_type_update=product_type_update,
        )

    def delete_product_type(self, db: Session, db_product_type: ProductType) -> ProductType:
        return self._runtime.delete_product_type(db=db, db_product_type=db_product_type)

    def create_attribute_template(
        self,
        db: Session,
        attr_template_create: schemas.AttributeTemplateCreate,
        product_type_id: int,
    ) -> AttributeTemplate:
        return self._runtime.create_attribute_template(
            db=db,
            attr_template_create=attr_template_create,
            product_type_id=product_type_id,
        )

    def get_attribute_template(
        self,
        db: Session,
        attribute_template_id: int,
    ) -> Optional[AttributeTemplate]:
        return self._runtime.get_attribute_template(
            db=db,
            attribute_template_id=attribute_template_id,
        )

    def update_attribute_template(
        self,
        db: Session,
        db_attr_template: AttributeTemplate,
        attr_template_update: schemas.AttributeTemplateUpdate,
    ) -> AttributeTemplate:
        return self._runtime.update_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
            attr_template_update=attr_template_update,
        )

    def delete_attribute_template(
        self,
        db: Session,
        db_attr_template: AttributeTemplate,
    ) -> AttributeTemplate:
        return self._runtime.delete_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
        )

    def reorder_attribute_template(
        self,
        db: Session,
        attribute_id: int,
        direction: str,
    ) -> Optional[AttributeTemplate]:
        return self._runtime.reorder_attribute_template(
            db=db,
            attribute_id=attribute_id,
            direction=direction,
        )


class _ProductTypeCrudRuntime:
    def create_product_type(
        self,
        db: Session,
        product_type_create: schemas.ProductTypeCreate,
        user_id: Optional[int] = None,
    ) -> ProductType:
        return _create_product_type_impl(
            db=db,
            product_type_create=product_type_create,
            user_id=user_id,
        )

    def get_product_type(self, db: Session, product_type_id: int) -> Optional[ProductType]:
        return _get_product_type_impl(db=db, product_type_id=product_type_id)

    def get_product_type_by_key_name(
        self,
        db: Session,
        key_name: str,
        user_id: Optional[int] = None,
    ) -> Optional[ProductType]:
        return _get_product_type_by_key_name_impl(
            db=db,
            key_name=key_name,
            user_id=user_id,
        )

    def get_product_types_for_user(
        self,
        db: Session,
        user_id: Optional[int],
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[ProductType]:
        return _get_product_types_for_user_impl(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            search=search,
        )

    def count_product_types_for_user(
        self,
        db: Session,
        user_id: Optional[int],
        search: Optional[str] = None,
    ) -> int:
        return _count_product_types_for_user_impl(
            db=db,
            user_id=user_id,
            search=search,
        )

    def update_product_type(
        self,
        db: Session,
        db_product_type: ProductType,
        product_type_update: schemas.ProductTypeUpdate,
    ) -> ProductType:
        return _update_product_type_impl(
            db=db,
            db_product_type=db_product_type,
            product_type_update=product_type_update,
        )

    def delete_product_type(self, db: Session, db_product_type: ProductType) -> ProductType:
        return _delete_product_type_impl(db=db, db_product_type=db_product_type)

    def create_attribute_template(
        self,
        db: Session,
        attr_template_create: schemas.AttributeTemplateCreate,
        product_type_id: int,
    ) -> AttributeTemplate:
        return _create_attribute_template_impl(
            db=db,
            attr_template_create=attr_template_create,
            product_type_id=product_type_id,
        )

    def get_attribute_template(
        self,
        db: Session,
        attribute_template_id: int,
    ) -> Optional[AttributeTemplate]:
        return _get_attribute_template_impl(
            db=db,
            attribute_template_id=attribute_template_id,
        )

    def update_attribute_template(
        self,
        db: Session,
        db_attr_template: AttributeTemplate,
        attr_template_update: schemas.AttributeTemplateUpdate,
    ) -> AttributeTemplate:
        return _update_attribute_template_impl(
            db=db,
            db_attr_template=db_attr_template,
            attr_template_update=attr_template_update,
        )

    def delete_attribute_template(
        self,
        db: Session,
        db_attr_template: AttributeTemplate,
    ) -> AttributeTemplate:
        return _delete_attribute_template_impl(
            db=db,
            db_attr_template=db_attr_template,
        )

    def reorder_attribute_template(
        self,
        db: Session,
        attribute_id: int,
        direction: str,
    ) -> Optional[AttributeTemplate]:
        return _reorder_attribute_template_impl(
            db=db,
            attribute_id=attribute_id,
            direction=direction,
        )


_product_type_workflow = _ProductTypeCrudWorkflow()


def create_product_type(
    db: Session,
    product_type_create: schemas.ProductTypeCreate,
    user_id: Optional[int] = None,
) -> ProductType:
    return _product_type_workflow.create_product_type(
        db=db,
        product_type_create=product_type_create,
        user_id=user_id,
    )


def get_product_type(db: Session, product_type_id: int) -> Optional[ProductType]:
    return _product_type_workflow.get_product_type(db=db, product_type_id=product_type_id)


def get_product_type_by_key_name(
    db: Session,
    key_name: str,
    user_id: Optional[int] = None,
) -> Optional[ProductType]:
    return _product_type_workflow.get_product_type_by_key_name(
        db=db,
        key_name=key_name,
        user_id=user_id,
    )


def get_product_types_for_user(
    db: Session,
    user_id: Optional[int],
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
) -> List[ProductType]:
    return _product_type_workflow.get_product_types_for_user(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        search=search,
    )


def count_product_types_for_user(
    db: Session,
    user_id: Optional[int],
    search: Optional[str] = None,
) -> int:
    return _product_type_workflow.count_product_types_for_user(
        db=db,
        user_id=user_id,
        search=search,
    )


def update_product_type(
    db: Session,
    db_product_type: ProductType,
    product_type_update: schemas.ProductTypeUpdate,
) -> ProductType:
    return _product_type_workflow.update_product_type(
        db=db,
        db_product_type=db_product_type,
        product_type_update=product_type_update,
    )


def delete_product_type(db: Session, db_product_type: ProductType) -> ProductType:
    return _product_type_workflow.delete_product_type(
        db=db,
        db_product_type=db_product_type,
    )


def create_attribute_template(
    db: Session,
    attr_template_create: schemas.AttributeTemplateCreate,
    product_type_id: int,
) -> AttributeTemplate:
    return _product_type_workflow.create_attribute_template(
        db=db,
        attr_template_create=attr_template_create,
        product_type_id=product_type_id,
    )


def get_attribute_template(
    db: Session,
    attribute_template_id: int,
) -> Optional[AttributeTemplate]:
    return _product_type_workflow.get_attribute_template(
        db=db,
        attribute_template_id=attribute_template_id,
    )


def update_attribute_template(
    db: Session,
    db_attr_template: AttributeTemplate,
    attr_template_update: schemas.AttributeTemplateUpdate,
) -> AttributeTemplate:
    return _product_type_workflow.update_attribute_template(
        db=db,
        db_attr_template=db_attr_template,
        attr_template_update=attr_template_update,
    )


def delete_attribute_template(
    db: Session,
    db_attr_template: AttributeTemplate,
) -> AttributeTemplate:
    return _product_type_workflow.delete_attribute_template(
        db=db,
        db_attr_template=db_attr_template,
    )


def reorder_attribute_template(
    db: Session,
    attribute_id: int,
    direction: str,
) -> Optional[AttributeTemplate]:
    return _product_type_workflow.reorder_attribute_template(
        db=db,
        attribute_id=attribute_id,
        direction=direction,
    )


class ProductTypeCrudLegacyService:
    def create_product_type(self, *args, **kwargs):
        return create_product_type(*args, **kwargs)

    def get_product_type(self, *args, **kwargs):
        return get_product_type(*args, **kwargs)

    def get_product_type_by_key_name(self, *args, **kwargs):
        return get_product_type_by_key_name(*args, **kwargs)

    def get_product_types_for_user(self, *args, **kwargs):
        return get_product_types_for_user(*args, **kwargs)

    def count_product_types_for_user(self, *args, **kwargs):
        return count_product_types_for_user(*args, **kwargs)

    def update_product_type(self, *args, **kwargs):
        return update_product_type(*args, **kwargs)

    def delete_product_type(self, *args, **kwargs):
        return delete_product_type(*args, **kwargs)

    def create_attribute_template(self, *args, **kwargs):
        return create_attribute_template(*args, **kwargs)

    def get_attribute_template(self, *args, **kwargs):
        return get_attribute_template(*args, **kwargs)

    def update_attribute_template(self, *args, **kwargs):
        return update_attribute_template(*args, **kwargs)

    def delete_attribute_template(self, *args, **kwargs):
        return delete_attribute_template(*args, **kwargs)

    def reorder_attribute_template(self, *args, **kwargs):
        return reorder_attribute_template(*args, **kwargs)


product_type_crud_legacy_service = ProductTypeCrudLegacyService()
