"""Repositorio de infraestrutura orientado a objetos para 'product_type_repository'."""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from Backend import schemas
from Backend.models import AttributeTemplate, ProductType, Produto

logger = logging.getLogger(__name__)

class ProductTypeRepository:
    """Repository OO de tipos de produto com Session vinculada por request."""

    def __init__(self, db: Session) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._db = db

    @staticmethod
    def _apply_product_type_search(query, search: Optional[str]):
        """Process Apply product type search."""
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

    def create_product_type(
        self,
        *,
        product_type_create: schemas.ProductTypeCreate,
        user_id: Optional[int] = None,
    ) -> ProductType:
        """Create product type."""
        existing_query = self._db.query(ProductType).filter(
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
            detail = f"Ja existe um Tipo de Produto com a chave '{product_type_create.key_name}'."
            if existing_product_type.user_id is None:
                detail = (
                    f"Um Tipo de Produto global com a chave '{product_type_create.key_name}' "
                    "ja existe e nao pode ser duplicado."
                )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

        db_product_type = ProductType(
            key_name=product_type_create.key_name,
            friendly_name=product_type_create.friendly_name,
            description=getattr(product_type_create, "description", None),
            user_id=user_id,
        )
        self._db.add(db_product_type)
        self._db.flush()

        if (
            hasattr(product_type_create, "attribute_templates")
            and product_type_create.attribute_templates
        ):
            for attribute_data in product_type_create.attribute_templates:
                db_attribute = AttributeTemplate(
                    **attribute_data.model_dump(),
                    product_type_id=db_product_type.id,
                )
                self._db.add(db_attribute)

        self._db.commit()
        self._db.refresh(db_product_type)
        self._db.refresh(db_product_type, attribute_names=["attribute_templates"])
        return db_product_type

    def get_product_type(self, *, product_type_id: int) -> Optional[ProductType]:
        """Return Product type."""
        return (
            self._db.query(ProductType)
            .options(selectinload(ProductType.attribute_templates))
            .filter(ProductType.id == product_type_id)
            .first()
        )

    def get_product_type_by_key_name(
        self,
        *,
        key_name: str,
        user_id: Optional[int] = None,
    ) -> Optional[ProductType]:
        """Return Product type by key name."""
        query = (
            self._db.query(ProductType)
            .options(selectinload(ProductType.attribute_templates))
            .filter(ProductType.key_name == key_name)
        )
        if user_id:
            return (
                query.filter(or_(ProductType.user_id == user_id, ProductType.user_id.is_(None)))
                .order_by(ProductType.user_id.desc())
                .first()
            )

        return query.filter(ProductType.user_id.is_(None)).first()

    def get_product_types_for_user(
        self,
        *,
        user_id: Optional[int],
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[ProductType]:
        """Return Product types for user."""
        query = self._db.query(ProductType).options(selectinload(ProductType.attribute_templates))
        if user_id:
            query = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id.is_(None)))
        else:
            query = query.filter(ProductType.user_id.is_(None))

        query = self._apply_product_type_search(query, search)
        return (
            query.order_by(ProductType.user_id.nullslast(), ProductType.friendly_name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_product_types_for_user(self, *, user_id: Optional[int], search: Optional[str] = None) -> int:
        """Count product types for user."""
        query = self._db.query(func.count(ProductType.id))
        if user_id:
            query = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id.is_(None)))
        else:
            query = query.filter(ProductType.user_id.is_(None))

        query = self._apply_product_type_search(query, search)
        count = query.scalar()
        return count if count is not None else 0

    def search_product_types_for_index(
        self,
        *,
        query_text: Optional[str],
        limit: int,
        user_id: Optional[int],
        is_admin: bool,
    ):
        """Return lightweight product-type rows for search endpoint rendering."""
        query = self._db.query(ProductType.id, ProductType.friendly_name, ProductType.created_at)
        if query_text:
            term = f"%{query_text.lower()}%"
            query = query.filter(func.lower(ProductType.friendly_name).ilike(term))
        if not is_admin:
            query = query.filter(
                (ProductType.user_id == user_id) | ProductType.user_id.is_(None)
            )
        return query.order_by(ProductType.created_at.desc()).limit(limit).all()

    def update_product_type(
        self,
        *,
        db_product_type: ProductType,
        product_type_update: schemas.ProductTypeUpdate,
    ) -> ProductType:
        """Update product type."""
        update_data = product_type_update.model_dump(exclude_unset=True)

        if "key_name" in update_data and update_data["key_name"] != db_product_type.key_name:
            existing_check = self._db.query(ProductType).filter(
                ProductType.key_name == update_data["key_name"],
                ProductType.id != db_product_type.id,
            )
            if db_product_type.user_id:
                existing_check = existing_check.filter(
                    or_(ProductType.user_id == db_product_type.user_id, ProductType.user_id.is_(None))
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

        self._db.commit()
        self._db.refresh(db_product_type)
        self._db.refresh(db_product_type, attribute_names=["attribute_templates"])
        return db_product_type

    def delete_product_type(self, *, db_product_type: ProductType) -> ProductType:
        """Delete product type."""
        associated_products = (
            self._db.query(Produto).filter(Produto.product_type_id == db_product_type.id).count()
        )
        if associated_products > 0:
            raise IntegrityError(
                (
                    f"Nao e possivel excluir o Tipo de Produto '{db_product_type.friendly_name}' "
                    f"pois ele esta associado a {associated_products} produto(s)."
                ),
                params={},
                orig=None,
            )

        self._db.delete(db_product_type)
        self._db.commit()
        return db_product_type

    def create_attribute_template(
        self,
        *,
        attr_template_create: schemas.AttributeTemplateCreate,
        product_type_id: int,
    ) -> AttributeTemplate:
        """Create attribute template."""
        existing_attribute = (
            self._db.query(AttributeTemplate)
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
        self._db.add(db_attr_template)
        self._db.commit()
        self._db.refresh(db_attr_template)
        return db_attr_template

    def get_attribute_template_by_key(
        self,
        *,
        product_type_id: int,
        attribute_key: str,
        exclude_attribute_id: Optional[int] = None,
    ) -> Optional[AttributeTemplate]:
        """Return attribute template by key in one product type scope."""
        query = self._db.query(AttributeTemplate).filter(
            AttributeTemplate.product_type_id == product_type_id,
            AttributeTemplate.attribute_key == attribute_key,
        )
        if exclude_attribute_id is not None:
            query = query.filter(AttributeTemplate.id != exclude_attribute_id)
        return query.first()

    def get_attribute_template(self, *, attribute_template_id: int) -> Optional[AttributeTemplate]:
        """Return Attribute template."""
        return (
            self._db.query(AttributeTemplate)
            .filter(AttributeTemplate.id == attribute_template_id)
            .first()
        )

    def update_attribute_template(
        self,
        *,
        db_attr_template: AttributeTemplate,
        attr_template_update: schemas.AttributeTemplateUpdate,
    ) -> AttributeTemplate:
        """Update attribute template."""
        update_data = attr_template_update.model_dump(exclude_unset=True)

        if "attribute_key" in update_data and update_data["attribute_key"] != db_attr_template.attribute_key:
            existing_check = (
                self._db.query(AttributeTemplate)
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
        self._db.commit()
        self._db.refresh(db_attr_template)
        return db_attr_template

    def delete_attribute_template(self, *, db_attr_template: AttributeTemplate) -> AttributeTemplate:
        """Delete attribute template."""
        self._db.delete(db_attr_template)
        self._db.commit()
        return db_attr_template

    def reorder_attribute_template(self, *, attribute_id: int, direction: str) -> Optional[AttributeTemplate]:
        """Process Reorder attribute template."""
        attr_to_move = self.get_attribute_template(attribute_template_id=attribute_id)
        if not attr_to_move:
            return None

        siblings = (
            self._db.query(AttributeTemplate)
            .filter(AttributeTemplate.product_type_id == attr_to_move.product_type_id)
            .order_by(AttributeTemplate.display_order.asc(), AttributeTemplate.id.asc())
            .all()
        )

        if any(sibling.display_order is None for sibling in siblings):
            for index, sibling in enumerate(siblings):
                sibling.display_order = index
            self._db.commit()
            self._db.refresh(attr_to_move)

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
            self._db.commit()
        elif direction == "down" and current_index < len(siblings) - 1:
            next_item = siblings[current_index + 1]
            next_item.display_order, attr_to_move.display_order = (
                attr_to_move.display_order,
                next_item.display_order,
            )
            self._db.commit()

        siblings_reordered = (
            self._db.query(AttributeTemplate)
            .filter(AttributeTemplate.product_type_id == attr_to_move.product_type_id)
            .order_by(AttributeTemplate.display_order.asc(), AttributeTemplate.id.asc())
            .all()
        )
        for index, sibling in enumerate(siblings_reordered):
            sibling.display_order = index

        self._db.commit()
        self._db.refresh(attr_to_move)
        return attr_to_move
