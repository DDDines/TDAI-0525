"""Repository coverage for suppliers and admin analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models, schemas
from Backend.database import Base
from Backend.infrastructure.repositories.admin_analytics_repository import AdminAnalyticsRepository
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository


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


def _create_user(session, *, email: str, plano_id: int | None = None):
    user = models.User(
        email=email,
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        plano_id=plano_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_plan(session, *, nome: str = "Plano Analytics"):
    plan = models.Plano(
        nome=nome,
        descricao=nome,
        preco_mensal=10.0,
        limite_produtos=10,
        limite_enriquecimento_web=20,
        limite_geracao_ia=30,
        permite_api_externa=False,
        suporte_prioritario=False,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _create_supplier(session, *, user_id: int, nome: str):
    fornecedor = models.Fornecedor(nome=nome, user_id=user_id)
    session.add(fornecedor)
    session.commit()
    session.refresh(fornecedor)
    return fornecedor


def _create_product(session, *, user_id: int, fornecedor_id: int | None = None, status=models.StatusEnriquecimentoEnum.NAO_INICIADO):
    product = models.Produto(
        user_id=user_id,
        nome_base=f"Produto {user_id}",
        fornecedor_id=fornecedor_id,
        status_enriquecimento_web=status,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


class _PayloadWithDump:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self, **_kwargs):
        return dict(self._payload)


def test_fornecedor_repository_crud_search_mapping_and_catalog_file_paths():
    engine, session = _build_session()
    try:
        owner = _create_user(session, email="owner@example.com")
        other = _create_user(session, email="other@example.com")
        repo = FornecedorRepository(session)

        created = repo.create_fornecedor(
            fornecedor=_PayloadWithDump(
                {
                    "nome": "Fornecedor Um",
                    "email_contato": "contato@example.com",
                    "site_url": 123,
                    "link_busca_padrao": 456,
                }
            ),
            user_id=owner.id,
        )
        assert created.site_url == "123"
        assert created.link_busca_padrao == "456"
        assert repo.get_fornecedor(fornecedor_id=created.id).id == created.id

        with pytest.raises(HTTPException) as duplicate_error:
            repo.create_fornecedor(
                fornecedor=schemas.FornecedorCreate(nome="Fornecedor Um"),
                user_id=owner.id,
            )
        assert duplicate_error.value.status_code == 409

        second = repo.create_fornecedor(
            fornecedor=schemas.FornecedorCreate(nome="Fornecedor Dois", contato_principal="Maria"),
            user_id=other.id,
        )
        assert second.id != created.id

        assert [item.id for item in repo.get_fornecedores_by_user(user_id=owner.id, is_admin=False)] == [created.id]
        assert {item.id for item in repo.get_fornecedores_by_user(is_admin=True)} == {created.id, second.id}
        assert repo.count_fornecedores_by_user(user_id=owner.id, is_admin=False, search="Fornecedor") == 1
        assert repo.search_fornecedores_for_index(query_text="Fornecedor", limit=10, user_id=owner.id, is_admin=False)[0].id == created.id
        assert repo.search_fornecedores_for_index(query_text=None, limit=10, user_id=None, is_admin=False) == []
        assert repo.exists_fornecedor_with_name_for_user(user_id=owner.id, nome="Fornecedor Um") is True
        assert repo.exists_fornecedor_with_name_for_user(user_id=owner.id, nome="Fornecedor Um", exclude_id=created.id) is False

        updated = repo.update_fornecedor(
            db_fornecedor=created,
            fornecedor_update=_PayloadWithDump(
                {
                    "nome": "Fornecedor Atualizado",
                    "site_url": 789,
                    "default_column_mapping": {"sku": "SKU"},
                }
            ),
        )
        assert updated.nome == "Fornecedor Atualizado"
        assert updated.site_url == "789"

        mapped = repo.set_default_column_mapping(
            db_fornecedor=updated,
            mapping={"nome": "Produto"},
        )
        assert mapped.default_column_mapping == {"nome": "Produto"}

        catalog_file = repo.create_catalog_import_file(
            user_id=owner.id,
            fornecedor_id=updated.id,
            file_name="catalogo.pdf",
            original_file_path="C:/tmp/uploads/catalogo-123.pdf",
        )
        assert catalog_file.original_filename == "catalogo.pdf"
        assert catalog_file.stored_filename == "catalogo-123.pdf"

        deleted = repo.delete_fornecedor(db_fornecedor=updated)
        assert deleted.id == created.id
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_admin_analytics_repository_counts_grouping_and_recent_queries():
    engine, session = _build_session()
    try:
        plan = _create_plan(session)
        owner = _create_user(session, email="owner@example.com", plano_id=plan.id)
        other = _create_user(session, email="other@example.com")
        supplier = _create_supplier(session, user_id=owner.id, nome="Fornecedor Analytics")
        product = _create_product(
            session,
            user_id=owner.id,
            fornecedor_id=supplier.id,
            status=models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO,
        )
        _create_product(session, user_id=other.id, status=models.StatusEnriquecimentoEnum.FALHOU)

        now = datetime.now(timezone.utc)
        recent_usage = models.RegistroUsoIA(
            user_id=owner.id,
            produto_id=product.id,
            tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
            status="SUCESSO",
            created_at=now,
        )
        old_usage = models.RegistroUsoIA(
            user_id=other.id,
            produto_id=None,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
            status="SUCESSO",
            created_at=now - timedelta(days=40),
        )
        session.add_all([recent_usage, old_usage])
        session.commit()

        repo = AdminAnalyticsRepository(session)
        start_at = now - timedelta(days=30)

        assert repo.count_total_users() == 2
        assert repo.count_total_products() == 2
        assert repo.count_total_suppliers() == 1
        assert repo.count_ia_usage_since(start_at=start_at) == 1
        assert repo.count_web_enrichment_usage_since(start_at=start_at) == 1
        assert repo.count_plan_usage_since(plano_id=plan.id, start_at=start_at) == 1
        assert repo.count_products_by_user(user_id=owner.id) == 1
        assert repo.count_ia_usage_by_user_since(user_id=owner.id, start_at=start_at) == 1
        assert repo.get_user_by_id(user_id=owner.id).email == "owner@example.com"

        grouped = repo.list_usage_by_action_since(start_at=start_at)
        assert [(row.tipo_acao, row.total_no_mes) for row in grouped] == [
            (models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO, 1)
        ]

        status_rows = repo.list_product_status_counts()
        assert {(row[0], row[1]) for row in status_rows} == {
            (models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO, 1),
            (models.StatusEnriquecimentoEnum.FALHOU, 1),
        }

        recent_records = repo.list_recent_usage_records(limit=5)
        assert [item.id for item in recent_records] == [recent_usage.id, old_usage.id]
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
