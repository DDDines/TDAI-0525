from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models, schemas
from Backend.application.services.product_management_service import ProductManagementService
from Backend.application.services.product_repositories import ProductRepositories
from Backend.database import Base
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
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


def _drop_collect_in_ai_from_attribute_templates(session) -> None:
    session.execute(text("DROP TABLE attribute_templates"))
    session.execute(
        text(
            """
            CREATE TABLE attribute_templates (
                id INTEGER PRIMARY KEY,
                product_type_id INTEGER NOT NULL,
                attribute_key VARCHAR NOT NULL,
                label VARCHAR NOT NULL,
                field_type VARCHAR NOT NULL DEFAULT 'TEXT',
                description TEXT,
                default_value VARCHAR,
                options JSON,
                is_required BOOLEAN DEFAULT 0,
                is_filterable BOOLEAN DEFAULT 0,
                display_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    session.commit()


def _drop_logo_url_from_fornecedores(session) -> None:
    session.execute(text("DROP TABLE fornecedores"))
    session.execute(
        text(
            """
            CREATE TABLE fornecedores (
                id INTEGER PRIMARY KEY,
                nome VARCHAR NOT NULL,
                email_contato VARCHAR,
                telefone_contato VARCHAR,
                endereco TEXT,
                site_url VARCHAR,
                termos_contratuais TEXT,
                contato_principal VARCHAR,
                observacoes TEXT,
                link_busca_padrao VARCHAR,
                default_column_mapping JSON,
                user_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    session.commit()


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


def _insert_legacy_attribute(session, *, product_type_id: int, attribute_key: str, label: str) -> None:
    session.execute(
        text(
            """
            INSERT INTO attribute_templates
                (product_type_id, attribute_key, label, field_type, display_order, is_required, is_filterable)
            VALUES
                (:product_type_id, :attribute_key, :label, :field_type, :display_order, 0, 0)
            """
        ),
        {
            "product_type_id": product_type_id,
            "attribute_key": attribute_key,
            "label": label,
            "field_type": "TEXT",
            "display_order": 0,
        },
    )
    session.commit()


def test_product_type_repository_recovers_legacy_collect_in_ai_column():
    engine, session = _build_session()
    try:
        _drop_collect_in_ai_from_attribute_templates(session)
        owner = _create_user(session, email="owner@example.com")
        product_type = _create_product_type(
            session,
            key_name="legacy-type",
            friendly_name="Legacy Type",
            user_id=owner.id,
        )
        _insert_legacy_attribute(
            session,
            product_type_id=product_type.id,
            attribute_key="material",
            label="Material",
        )

        repo = ProductTypeRepository(session)
        visible = repo.get_product_types_for_user(user_id=owner.id, skip=0, limit=10)

        attribute_columns = {
            column["name"] for column in inspect(session.get_bind()).get_columns("attribute_templates")
        }
        assert "collect_in_ai" in attribute_columns
        assert visible[0].attribute_templates[0].collect_in_ai is True
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_admin_product_listing_serializes_when_attribute_templates_need_runtime_compatibility():
    engine, session = _build_session()
    try:
        _drop_collect_in_ai_from_attribute_templates(session)
        admin = _create_user(session, email="admin@example.com", is_superuser=True)
        product_type = _create_product_type(
            session,
            key_name="compat-admin",
            friendly_name="Compat Admin",
            user_id=None,
        )
        _insert_legacy_attribute(
            session,
            product_type_id=product_type.id,
            attribute_key="acabamento",
            label="Acabamento",
        )

        product = models.Produto(
            user_id=admin.id,
            nome_base="Produto legado",
            sku="LEGACY-1",
            product_type_id=product_type.id,
        )
        session.add(product)
        session.commit()

        service = ProductManagementService(
            models=models,
            schemas=schemas,
            **ProductRepositories.build_product_management_repositories(session=session),
        )

        payload = service.list_produtos(
            skip=0,
            limit=10,
            sort_by="id",
            sort_order="desc",
            search=None,
            fornecedor_id=None,
            categoria=None,
            status_enriquecimento_web=None,
            status_titulo_ia=None,
            status_descricao_ia=None,
            product_type_id=None,
            enrichment_scope=None,
            current_user=admin,
        )
        page = schemas.ProdutoPage.model_validate(payload)

        assert page.total_items == 1
        assert page.items[0].nome_base == "Produto legado"
        assert page.items[0].product_type.attribute_templates[0].collect_in_ai is True
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_fornecedor_repository_recovers_legacy_logo_url_column():
    engine, session = _build_session()
    try:
        _drop_logo_url_from_fornecedores(session)
        owner = _create_user(session, email="supplier-owner@example.com")

        session.execute(
            text(
                """
                INSERT INTO fornecedores (nome, site_url, user_id)
                VALUES (:nome, :site_url, :user_id)
                """
            ),
            {
                "nome": "Fornecedor legado",
                "site_url": "https://fornecedor.test",
                "user_id": owner.id,
            },
        )
        session.commit()

        repo = FornecedorRepository(session)
        visible = repo.get_fornecedores_by_user(
            user_id=owner.id,
            is_admin=False,
            skip=0,
            limit=10,
        )

        fornecedor_columns = {
            column["name"] for column in inspect(session.get_bind()).get_columns("fornecedores")
        }
        assert "logo_url" in fornecedor_columns
        assert visible[0].nome == "Fornecedor legado"
        assert visible[0].logo_url is None
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
