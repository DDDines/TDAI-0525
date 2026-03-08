"""Risk-focused tests for the product type repository."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models, schemas
from Backend.database import Base
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository


def _build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    return engine, session


def _create_user(session, *, email: str, is_superuser: bool = False):
    user = models.User(
        email=email,
        hashed_password="hashed",
        is_active=True,
        is_superuser=is_superuser,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_product_type(session, *, key_name: str, friendly_name: str, user_id=None):
    product_type = models.ProductType(
        key_name=key_name,
        friendly_name=friendly_name,
        description=f"Descricao {friendly_name}",
        user_id=user_id,
    )
    session.add(product_type)
    session.commit()
    session.refresh(product_type)
    return product_type


def _create_attribute(
    session,
    *,
    product_type_id: int,
    attribute_key: str,
    label: str,
    display_order: int,
):
    attribute = models.AttributeTemplate(
        product_type_id=product_type_id,
        attribute_key=attribute_key,
        label=label,
        field_type=models.AttributeFieldTypeEnum.TEXT,
        display_order=display_order,
    )
    session.add(attribute)
    session.commit()
    session.refresh(attribute)
    return attribute


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""

    @staticmethod
    def test_repository_returns_global_and_user_types_with_search_and_count():
        """Return global and user-scoped product types with search support."""
        engine, session = _build_session()
        try:
            owner = _create_user(session, email="owner@example.com")
            other = _create_user(session, email="other@example.com")
            repo = ProductTypeRepository(session)

            global_type = _create_product_type(
                session,
                key_name="global-freios",
                friendly_name="Freios Global",
                user_id=None,
            )
            user_type = _create_product_type(
                session,
                key_name="freios-pesados",
                friendly_name="Freios Pesados",
                user_id=owner.id,
            )
            _create_product_type(
                session,
                key_name="eletrica",
                friendly_name="Eletrica",
                user_id=other.id,
            )

            visible = repo.get_product_types_for_user(user_id=owner.id, skip=0, limit=10)
            visible_ids = {item.id for item in visible}
            assert global_type.id in visible_ids
            assert user_type.id in visible_ids
            assert len(visible_ids) == 2

            searched = repo.get_product_types_for_user(
                user_id=owner.id,
                skip=0,
                limit=10,
                search="pesados",
            )
            assert [item.id for item in searched] == [user_type.id]
            assert repo.count_product_types_for_user(user_id=owner.id, search="freios") == 2
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)

    @staticmethod
    def test_repository_create_product_type_rejects_duplicate_global_key_for_user():
        """Reject user-scoped type creation when a global key already exists."""
        engine, session = _build_session()
        try:
            owner = _create_user(session, email="owner@example.com")
            repo = ProductTypeRepository(session)
            _create_product_type(
                session,
                key_name="reservatorios",
                friendly_name="Reservatorios Global",
                user_id=None,
            )

            with pytest.raises(Exception) as exc_info:
                repo.create_product_type(
                    product_type_create=schemas.ProductTypeCreate(
                        key_name="reservatorios",
                        friendly_name="Reservatorios do Usuario",
                    ),
                    user_id=owner.id,
                )

            assert "ja existe" in str(exc_info.value).lower()
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)

    @staticmethod
    def test_repository_delete_product_type_rejects_when_linked_to_products():
        """Reject deleting types that are already linked to products."""
        engine, session = _build_session()
        try:
            owner = _create_user(session, email="owner@example.com")
            repo = ProductTypeRepository(session)
            product_type = _create_product_type(
                session,
                key_name="lataria",
                friendly_name="Lataria",
                user_id=owner.id,
            )
            session.add(
                models.Produto(
                    user_id=owner.id,
                    nome_base="Produto Vinculado",
                    product_type_id=product_type.id,
                )
            )
            session.commit()

            with pytest.raises(IntegrityError):
                repo.delete_product_type(db_product_type=product_type)
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)

    @staticmethod
    def test_repository_reorders_attributes_and_normalizes_positions():
        """Reorder attributes and normalize display order after the swap."""
        engine, session = _build_session()
        try:
            owner = _create_user(session, email="owner@example.com")
            repo = ProductTypeRepository(session)
            product_type = _create_product_type(
                session,
                key_name="suspensao",
                friendly_name="Suspensao",
                user_id=owner.id,
            )
            first_attr = _create_attribute(
                session,
                product_type_id=product_type.id,
                attribute_key="material",
                label="Material",
                display_order=0,
            )
            second_attr = _create_attribute(
                session,
                product_type_id=product_type.id,
                attribute_key="acabamento",
                label="Acabamento",
                display_order=1,
            )

            moved = repo.reorder_attribute_template(attribute_id=first_attr.id, direction="down")
            assert moved.id == first_attr.id

            ordered = (
                session.query(models.AttributeTemplate)
                .filter(models.AttributeTemplate.product_type_id == product_type.id)
                .order_by(models.AttributeTemplate.display_order.asc(), models.AttributeTemplate.id.asc())
                .all()
            )
            assert [item.attribute_key for item in ordered] == ["acabamento", "material"]
            assert [item.display_order for item in ordered] == [0, 1]
            assert second_attr.id == ordered[0].id
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)

    @staticmethod
    def test_repository_update_attribute_rejects_duplicate_key():
        """Reject attribute key collisions inside the same product type."""
        engine, session = _build_session()
        try:
            owner = _create_user(session, email="owner@example.com")
            repo = ProductTypeRepository(session)
            product_type = _create_product_type(
                session,
                key_name="acessorios",
                friendly_name="Acessorios",
                user_id=owner.id,
            )
            attribute = _create_attribute(
                session,
                product_type_id=product_type.id,
                attribute_key="cor",
                label="Cor",
                display_order=0,
            )
            _create_attribute(
                session,
                product_type_id=product_type.id,
                attribute_key="material",
                label="Material",
                display_order=1,
            )

            with pytest.raises(IntegrityError):
                repo.update_attribute_template(
                    db_attr_template=attribute,
                    attr_template_update=schemas.AttributeTemplateUpdate(attribute_key="material"),
                )
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)


test_repository_returns_global_and_user_types_with_search_and_count = (
    _TopLevelFunctionSurface.test_repository_returns_global_and_user_types_with_search_and_count
)
test_repository_create_product_type_rejects_duplicate_global_key_for_user = (
    _TopLevelFunctionSurface.test_repository_create_product_type_rejects_duplicate_global_key_for_user
)
test_repository_delete_product_type_rejects_when_linked_to_products = (
    _TopLevelFunctionSurface.test_repository_delete_product_type_rejects_when_linked_to_products
)
test_repository_reorders_attributes_and_normalizes_positions = (
    _TopLevelFunctionSurface.test_repository_reorders_attributes_and_normalizes_positions
)
test_repository_update_attribute_rejects_duplicate_key = (
    _TopLevelFunctionSurface.test_repository_update_attribute_rejects_duplicate_key
)


def test_repository_create_update_and_lookup_product_types_and_attributes():
    engine, session = _build_session()
    try:
        owner = _create_user(session, email="owner@example.com")
        repo = ProductTypeRepository(session)

        created = repo.create_product_type(
            product_type_create=schemas.ProductTypeCreate(
                key_name="motores",
                friendly_name="Motores",
                description="Linha de motores",
                attribute_templates=[
                    schemas.AttributeTemplateCreate(
                        attribute_key="potencia",
                        label="Potencia",
                        display_order=0,
                    )
                ],
            ),
            user_id=owner.id,
        )
        assert created.user_id == owner.id
        assert [item.attribute_key for item in created.attribute_templates] == ["potencia"]

        global_created = repo.create_product_type(
            product_type_create=schemas.ProductTypeCreate(
                key_name="globais",
                friendly_name="Globais",
            ),
            user_id=None,
        )
        assert global_created.user_id is None

        fetched = repo.get_product_type(product_type_id=created.id)
        assert fetched.id == created.id

        by_key = repo.get_product_type_by_key_name(key_name="motores", user_id=owner.id)
        assert by_key.id == created.id
        assert repo.get_product_type_by_key_name(key_name="motores", user_id=None) is None
        assert repo.get_product_types_for_user(user_id=None, skip=0, limit=10)[0].id == global_created.id
        assert repo.count_product_types_for_user(user_id=None) == 1

        updated = repo.update_product_type(
            db_product_type=created,
            product_type_update=schemas.ProductTypeUpdate(
                friendly_name="Motores Pesados",
                description="Atualizado",
            ),
        )
        assert updated.friendly_name == "Motores Pesados"
        assert updated.description == "Atualizado"

        created_attr = repo.create_attribute_template(
            product_type_id=created.id,
            attr_template_create=schemas.AttributeTemplateCreate(
                attribute_key="voltagem",
                label="Voltagem",
                display_order=1,
            ),
        )
        assert created_attr.attribute_key == "voltagem"
        assert repo.get_attribute_template(attribute_template_id=created_attr.id).id == created_attr.id
        assert (
            repo.get_attribute_template_by_key(
                product_type_id=created.id,
                attribute_key="voltagem",
                exclude_attribute_id=created_attr.id,
            )
            is None
        )

        repo.update_attribute_template(
            db_attr_template=created_attr,
            attr_template_update=schemas.AttributeTemplateUpdate(label="Voltagem Nominal"),
        )
        assert created_attr.label == "Voltagem Nominal"

        deleted_attr = repo.delete_attribute_template(db_attr_template=created_attr)
        assert deleted_attr.id == created_attr.id
        assert repo.get_attribute_template(attribute_template_id=created_attr.id) is None
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_repository_search_and_conflict_paths_for_product_types_and_attributes():
    engine, session = _build_session()
    try:
        owner = _create_user(session, email="owner@example.com")
        other = _create_user(session, email="other@example.com")
        repo = ProductTypeRepository(session)

        global_type = _create_product_type(
            session,
            key_name="global-key",
            friendly_name="Global Key",
            user_id=None,
        )
        user_type = _create_product_type(
            session,
            key_name="user-key",
            friendly_name="User Key",
            user_id=owner.id,
        )
        _create_product_type(
            session,
            key_name="other-key",
            friendly_name="Other Key",
            user_id=other.id,
        )

        rows = repo.search_product_types_for_index(
            query_text="key",
            limit=10,
            user_id=owner.id,
            is_admin=False,
        )
        assert {row.id for row in rows} == {global_type.id, user_type.id}

        with pytest.raises(IntegrityError):
            repo.update_product_type(
                db_product_type=user_type,
                product_type_update=schemas.ProductTypeUpdate(key_name="global-key"),
            )

        with pytest.raises(HTTPException):
            repo.create_product_type(
                product_type_create=schemas.ProductTypeCreate(
                    key_name="global-key",
                    friendly_name="Global Duplicado",
                ),
                user_id=None,
            )

        created_attr = repo.create_attribute_template(
            product_type_id=user_type.id,
            attr_template_create=schemas.AttributeTemplateCreate(
                attribute_key="material",
                label="Material",
            ),
        )
        with pytest.raises(IntegrityError):
            repo.create_attribute_template(
                product_type_id=user_type.id,
                attr_template_create=schemas.AttributeTemplateCreate(
                    attribute_key="material",
                    label="Material",
                ),
            )

        created_attr.display_order = None
        session.commit()
        moved = repo.reorder_attribute_template(attribute_id=created_attr.id, direction="up")
        assert moved.id == created_attr.id
        assert moved.display_order == 0
        assert repo.reorder_attribute_template(attribute_id=99999, direction="up") is None

        first_attr = repo.create_attribute_template(
            product_type_id=user_type.id,
            attr_template_create=schemas.AttributeTemplateCreate(
                attribute_key="acabamento",
                label="Acabamento",
                display_order=1,
            ),
        )
        moved_up = repo.reorder_attribute_template(attribute_id=first_attr.id, direction="up")
        assert moved_up.id == first_attr.id
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_repository_covers_duplicate_user_key_and_unique_update_paths():
    engine, session = _build_session()
    try:
        owner = _create_user(session, email="owner@example.com")
        repo = ProductTypeRepository(session)
        _create_product_type(
            session,
            key_name="cabines",
            friendly_name="Cabines",
            user_id=owner.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            repo.create_product_type(
                product_type_create=schemas.ProductTypeCreate(
                    key_name="cabines",
                    friendly_name="Cabines 2",
                ),
                user_id=owner.id,
            )

        assert "ja existe" in exc_info.value.detail.lower()

        fresh_type = _create_product_type(
            session,
            key_name="escapamentos",
            friendly_name="Escapamentos",
            user_id=owner.id,
        )
        updated = repo.update_product_type(
            db_product_type=fresh_type,
            product_type_update=schemas.ProductTypeUpdate(key_name="escapamentos-pesados"),
        )
        assert updated.key_name == "escapamentos-pesados"

        attr = repo.create_attribute_template(
            product_type_id=fresh_type.id,
            attr_template_create=schemas.AttributeTemplateCreate(
                attribute_key="material",
                label="Material",
            ),
        )
        assert (
            repo.get_attribute_template_by_key(
                product_type_id=fresh_type.id,
                attribute_key="material",
            ).id
            == attr.id
        )

        updated_attr = repo.update_attribute_template(
            db_attr_template=attr,
            attr_template_update=schemas.AttributeTemplateUpdate(attribute_key="material-base"),
        )
        assert updated_attr.attribute_key == "material-base"
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
