"""Coverage-oriented tests for the user repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models, schemas
from Backend.database import Base
from Backend.infrastructure.repositories import user_repository as user_repository_module
from Backend.infrastructure.repositories.user_repository import UserRepository


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


def _create_plan(session, *, nome: str = "Pro", limite_produtos: int = 50):
    plan = models.Plano(
        nome=nome,
        descricao=f"Plano {nome}",
        preco_mensal=99.0,
        limite_produtos=limite_produtos,
        limite_enriquecimento_web=200,
        limite_geracao_ia=300,
        permite_api_externa=True,
        suporte_prioritario=True,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _create_role(session, *, name: str = "user"):
    role = models.Role(name=name, description=f"Role {name}")
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def test_user_repository_crud_plan_role_and_password_reset_paths(monkeypatch):
    engine, session = _build_session()
    try:
        monkeypatch.setattr(user_repository_module.settings, "DEFAULT_LIMIT_PRODUTOS_SEM_PLANO", 10, raising=False)
        monkeypatch.setattr(user_repository_module.settings, "DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO", 20, raising=False)
        monkeypatch.setattr(user_repository_module.settings, "DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO", 30, raising=False)

        repo = UserRepository(session)
        repo._security_workflow = SimpleNamespace(get_password_hash=lambda password: f"hash:{password}")

        base_plan = _create_plan(session, nome="Base", limite_produtos=25)
        _create_role(session, name="user")

        created = repo.create_user(
            user=schemas.UserCreate(
                email="julio@example.com",
                password="secret",
                nome_completo="Julio",
                plano_id=base_plan.id,
            )
        )
        assert created.hashed_password == "hash:secret"
        assert created.plano_id == base_plan.id
        assert created.limite_produtos == 25
        assert repo.get_user(user_id=created.id).id == created.id
        assert repo.get_user_by_email(email="julio@example.com").id == created.id
        assert repo.get_users(skip=0, limit=10)[0].id == created.id
        assert repo.search_users_by_email(query_text="julio", limit=10)[0].id == created.id

        updated = repo.update_user(
            db_user=created,
            user_update=schemas.UserUpdateByAdmin(
                nome_completo="Julio Cesar",
                password="nova",
                plano_id=None,
                is_active=False,
            ),
        )
        assert updated.nome_completo == "Julio Cesar"
        assert updated.hashed_password == "hash:nova"
        assert updated.is_active is False
        assert updated.plano_id is None
        assert updated.limite_produtos == 10
        assert updated.limite_enriquecimento_web == 20
        assert updated.limite_geracao_ia == 30

        updated_oauth = repo.update_user(
            db_user=updated,
            user_update=schemas.UserUpdateOAuth(nome_completo="Julio OAuth", avatar_url="https://avatar"),
        )
        assert updated_oauth.nome_completo == "Julio OAuth"
        assert updated_oauth.avatar_url == "https://avatar"

        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        repo.set_user_password_reset_token(
            user=updated,
            token_hash="token-hash",
            expires_at=expires_at,
        )
        assert repo.get_user_by_reset_token(token_hash="token-hash").id == updated.id

        created_role = repo.create_role(role=schemas.RoleCreate(name="admin", description="Administrador"))
        assert repo.get_role(role_id=created_role.id).name == "admin"
        assert repo.get_role_by_name(name="admin").id == created_role.id
        assert {item.name for item in repo.get_roles(skip=0, limit=10)} >= {"user", "admin"}

        created_plan = repo.create_plano(
            plano=schemas.PlanoCreate(
                nome="Enterprise",
                descricao="Maior",
                preco_mensal=199.0,
                limite_produtos=500,
                limite_enriquecimento_web=900,
                limite_geracao_ia=1200,
                permite_api_externa=True,
                suporte_prioritario=True,
            )
        )
        assert repo.get_plano(plano_id=created_plan.id).id == created_plan.id
        assert repo.get_plano_by_name(nome="Enterprise").id == created_plan.id
        assert {item.nome for item in repo.get_planos(skip=0, limit=10)} >= {"Base", "Enterprise"}

        updated_plan = repo.update_plano(
            db_plano=created_plan,
            plano_update=schemas.PlanoUpdate(nome="Enterprise Plus", preco_mensal=249.0),
        )
        assert updated_plan.nome == "Enterprise Plus"
        assert updated_plan.preco_mensal == 249.0

        deleted_plan = repo.delete_plano(db_plano=updated_plan)
        assert deleted_plan.id == created_plan.id
        deleted_user = repo.delete_user(db_user=updated)
        assert deleted_user.id == created.id
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_repository_duplicate_email_oauth_and_missing_plan_paths(monkeypatch):
    engine, session = _build_session()
    try:
        monkeypatch.setattr(user_repository_module.settings, "DEFAULT_LIMIT_PRODUTOS_SEM_PLANO", 11, raising=False)
        monkeypatch.setattr(user_repository_module.settings, "DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO", 22, raising=False)
        monkeypatch.setattr(user_repository_module.settings, "DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO", 33, raising=False)

        repo = UserRepository(session)
        repo._security_workflow = SimpleNamespace(get_password_hash=lambda password: f"hash:{password}")
        default_plan = _create_plan(session, nome="Starter", limite_produtos=15)
        default_role = _create_role(session, name="user")

        first = repo.create_user(
            user=schemas.UserCreate(
                email="duplicate@example.com",
                password="secret",
                plano_id=99999,
            )
        )
        assert first.plano_id is None
        assert first.limite_produtos == 11

        with pytest.raises(HTTPException) as duplicate_error:
            repo.create_user(
                user=schemas.UserCreate(
                    email="duplicate@example.com",
                    password="secret",
                )
            )
        assert duplicate_error.value.status_code == 400

        oauth_user = repo.create_user_oauth(
            user_oauth=schemas.UserCreateOAuth(
                email="oauth@example.com",
                nome_completo="OAuth User",
                provider="google",
                provider_user_id="google-123",
            ),
            plano_id_default=default_plan.id,
        )
        assert oauth_user.role_id == default_role.id
        assert oauth_user.plano_id == default_plan.id
        assert repo.get_user_by_provider(provider="google", provider_user_id="google-123").id == oauth_user.id

        with pytest.raises(HTTPException) as duplicate_oauth_error:
            repo.create_user_oauth(
                user_oauth=schemas.UserCreateOAuth(
                    email="oauth@example.com",
                    provider="google",
                    provider_user_id="google-456",
                ),
                plano_id_default=default_plan.id,
            )
        assert duplicate_oauth_error.value.status_code == 400

        oauth_without_plan = repo.create_user_oauth(
            user_oauth=schemas.UserCreateOAuth(
                email="oauth-sem-plano@example.com",
                nome_completo="OAuth Sem Plano",
                provider="google",
                provider_user_id="google-789",
            ),
            plano_id_default=99999,
        )
        assert oauth_without_plan.plano_id is None
        assert oauth_without_plan.role_id == default_role.id
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
