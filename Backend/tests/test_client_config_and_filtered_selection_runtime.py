"""Coverage for client credentials, experience mode and filtered bulk-selection helpers."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models
from Backend.database import Base
from Backend.infrastructure.repositories.external_credential_repository import (
    ExternalCredentialRepository,
)
from Backend.infrastructure.repositories.basic_generation_template_repository import (
    BasicGenerationTemplateRepository,
)
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository


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


def _create_plan(session, *, nome: str):
    plan = models.Plano(
        nome=nome,
        descricao=nome,
        preco_mensal=10.0,
        limite_produtos=10,
        limite_enriquecimento_web=20,
        limite_geracao_ia=30,
        permite_api_externa=True,
        suporte_prioritario=False,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _create_user(session, *, email: str, plano_id: int | None = None, nome_empresa: str | None = None):
    user = models.User(
        email=email,
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        plano_id=plano_id,
        nome_empresa=nome_empresa,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_supplier(session, *, user_id: int, nome: str):
    supplier = models.Fornecedor(nome=nome, user_id=user_id)
    session.add(supplier)
    session.commit()
    session.refresh(supplier)
    return supplier


def _create_product(session, *, user_id: int, nome_base: str, status):
    product = models.Produto(
        user_id=user_id,
        nome_base=nome_base,
        status_enriquecimento_web=status,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def test_external_credentials_follow_user_company_system_precedence():
    engine, session = _build_session()
    try:
        plano_gratuito = _create_plan(session, nome="Gratuito")
        plano_pro = _create_plan(session, nome="Pro")
        basic_user = _create_user(session, email="basic@example.com", plano_id=plano_gratuito.id)
        pro_user = _create_user(
            session,
            email="pro@example.com",
            plano_id=plano_pro.id,
            nome_empresa="Catalog AI LTDA",
        )
        repository = ExternalCredentialRepository(session)
        settings = SimpleNamespace(
            OPENAI_API_KEY="sk-system-openai",
            GOOGLE_GEMINI_API_KEY="gm-system",
            GOOGLE_CSE_API_KEY="AIza-system-cse",
            GOOGLE_CSE_ID="cse-system",
        )

        assert basic_user.product_experience_mode == "basic"
        assert pro_user.product_experience_mode == "complete"
        assert pro_user.company_identifier == "catalog-ai-ltda"

        repository.upsert_config(
            scope_type=models.ExternalCredentialScopeEnum.COMPANY,
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
            secret_value="sk-company-openai",
            config_json=None,
            description="Conta da empresa",
            is_active=True,
        )
        repository.upsert_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
            secret_value="sk-user-openai",
            config_json=None,
            description="Override pessoal",
            is_active=True,
        )

        effective_user = repository.resolve_effective_source(
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
            settings=settings,
        )
        assert effective_user["source"] == "user"
        assert effective_user["source_label"] == "Pessoal"
        assert effective_user["secret_value"] == "sk-user-openai"

        repository.upsert_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
            secret_value=None,
            config_json=None,
            description="Override pessoal atualizado",
            is_active=True,
        )
        preserved_user = repository.get_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
        )
        assert preserved_user.secret_value == "sk-user-openai"
        assert preserved_user.description == "Override pessoal atualizado"

        repository.delete_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
        )
        effective_company = repository.resolve_effective_source(
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
            settings=settings,
        )
        assert effective_company["source"] == "company"
        assert effective_company["source_label"] == "Empresa"
        assert effective_company["secret_value"] == "sk-company-openai"

        company_config = repository.get_config(
            scope_type=models.ExternalCredentialScopeEnum.COMPANY,
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
        )
        company_config.is_active = False
        session.add(company_config)
        session.commit()

        effective_system = repository.resolve_effective_source(
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=pro_user,
            settings=settings,
        )
        assert effective_system["source"] == "system"
        assert effective_system["source_label"] == "Sistema"
        assert effective_system["secret_value"] == "sk-system-openai"

        invalid_google_cse = repository.validate_payload(
            provider=models.ExternalCredentialProviderEnum.GOOGLE_CSE,
            secret_value="AIza-client",
            config_json={},
        )
        assert invalid_google_cse["valid"] is False
        assert "Search Engine ID" in invalid_google_cse["errors"][0]
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_basic_generation_templates_follow_user_company_system_precedence():
    engine, session = _build_session()
    try:
        plano_pro = _create_plan(session, nome="Pro")
        user = _create_user(
            session,
            email="templates@example.com",
            plano_id=plano_pro.id,
            nome_empresa="Catalog AI LTDA",
        )
        repository = BasicGenerationTemplateRepository(session)

        system_defaults = repository.system_defaults()
        effective_system = repository.resolve_effective_config(current_user=user)
        assert effective_system["source"] == "system"
        assert effective_system["title_template"] == system_defaults["title_template"]

        repository.upsert_config(
            scope_type=models.ExternalCredentialScopeEnum.COMPANY,
            current_user=user,
            title_template="{nome_base} {sku}",
            description_template="{nome_base}\n{specs}",
            is_active=True,
        )
        effective_company = repository.resolve_effective_config(current_user=user)
        assert effective_company["source"] == "company"
        assert effective_company["title_template"] == "{nome_base} {sku}"

        repository.upsert_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            current_user=user,
            title_template="{titulo_base} {reference}",
            description_template="{nome_base}\n{bullets}",
            is_active=True,
        )
        effective_user = repository.resolve_effective_config(current_user=user)
        assert effective_user["source"] == "user"
        assert effective_user["title_template"] == "{titulo_base} {reference}"

        overview = repository.build_overview(current_user=user)
        assert overview["company_identifier"] == "catalog-ai-ltda"
        assert overview["company_config"]["title_template"] == "{nome_base} {sku}"
        assert overview["user_config"]["title_template"] == "{titulo_base} {reference}"
        assert overview["effective_config"]["source"] == "user"

        repository.delete_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            current_user=user,
        )
        fallback_company = repository.resolve_effective_config(current_user=user)
        assert fallback_company["source"] == "company"

        repository.delete_config(
            scope_type=models.ExternalCredentialScopeEnum.COMPANY,
            current_user=user,
        )
        fallback_system = repository.resolve_effective_config(current_user=user)
        assert fallback_system["source"] == "system"
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_filtered_selection_helpers_cover_products_and_suppliers():
    engine, session = _build_session()
    try:
        owner = _create_user(session, email="owner@example.com")
        other = _create_user(session, email="other@example.com")
        supplier_alpha = _create_supplier(session, user_id=owner.id, nome="Fornecedor Alfa")
        _create_supplier(session, user_id=owner.id, nome="Fornecedor Beta")
        _create_supplier(session, user_id=other.id, nome="Fornecedor Alfa Externo")

        pending = _create_product(
            session,
            user_id=owner.id,
            nome_base="Bomba Pendente",
            status=models.StatusEnriquecimentoEnum.PENDENTE,
        )
        enriched = _create_product(
            session,
            user_id=owner.id,
            nome_base="Bomba Enriquecida",
            status=models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO,
        )
        partial = _create_product(
            session,
            user_id=owner.id,
            nome_base="Bomba Parcial",
            status=models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS,
        )
        failed = _create_product(
            session,
            user_id=owner.id,
            nome_base="Bomba Falhou",
            status=models.StatusEnriquecimentoEnum.FALHOU,
        )
        _create_product(
            session,
            user_id=other.id,
            nome_base="Bomba Externa",
            status=models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO,
        )

        product_repo = ProductRepository(session)
        supplier_repo = FornecedorRepository(session)

        assert product_repo.list_produto_ids_by_user(
            user_id=owner.id,
            is_admin=False,
            search="Bomba",
            enrichment_scope="enriched",
        ) == [enriched.id, partial.id]
        assert product_repo.list_produto_ids_by_user(
            user_id=owner.id,
            is_admin=False,
            enrichment_scope="pending",
        ) == [pending.id]
        assert product_repo.list_produto_ids_by_user(
            user_id=owner.id,
            is_admin=False,
            enrichment_scope="failed",
        ) == [failed.id]
        assert product_repo.list_produto_ids_by_user(
            user_id=None,
            is_admin=False,
        ) == []

        assert supplier_repo.list_fornecedor_ids_by_user(
            user_id=owner.id,
            is_admin=False,
            search="Alfa",
        ) == [supplier_alpha.id]
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
