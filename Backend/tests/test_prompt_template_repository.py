"""Tests for versioned prompt repository defaults and rendering paths."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.database import Base
from Backend.infrastructure.repositories.prompt_template_repository import (
    DEFAULT_PROMPT_TEMPLATES,
    PromptLookupResult,
    PromptTemplateName,
    PromptTemplateRepository,
    PromptTemplateResolver,
)
from Backend.models import PromptTemplate


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_prompt_template_repository_returns_default_when_table_is_empty(db_session):
    repository = PromptTemplateRepository(db_session)

    result = repository.get_prompt(nome=PromptTemplateName.IA_OPENAI_TITLE_SYSTEM)

    assert isinstance(result, PromptLookupResult)
    assert result.source == "default"
    assert result.versao == 0
    assert result.conteudo == DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_TITLE_SYSTEM]


def test_prompt_template_repository_returns_latest_version_and_renders_context(db_session):
    db_session.add(
        PromptTemplate(
            nome=PromptTemplateName.IA_GEMINI_DESCRIPTION_USER,
            conteudo="Descricao {nome_base} {modelo}",
            versao=1,
        )
    )
    db_session.add(
        PromptTemplate(
            nome=PromptTemplateName.IA_GEMINI_DESCRIPTION_USER,
            conteudo="Descricao nova {nome_base} {modelo}",
            versao=2,
        )
    )
    db_session.commit()

    repository = PromptTemplateRepository(db_session)
    latest = repository.get_latest_template(nome=PromptTemplateName.IA_GEMINI_DESCRIPTION_USER)
    rendered = repository.render_prompt(
        nome=PromptTemplateName.IA_GEMINI_DESCRIPTION_USER,
        context={"nome_base": "Paralama", "modelo": "X1"},
    )

    assert latest is not None
    assert latest.versao == 2
    assert rendered.source == "database"
    assert rendered.versao == 2
    assert rendered.conteudo == "Descricao nova Paralama X1"


def test_prompt_template_repository_render_prompt_uses_partial_safe_defaults(db_session):
    repository = PromptTemplateRepository(db_session)

    rendered = repository.render_prompt(
        nome=PromptTemplateName.IA_OPENAI_DESCRIPTION_USER,
        context={"nome_base": "Reservatorio"},
    )

    assert rendered.source == "default"
    assert "Reservatorio" in rendered.conteudo
    assert "Marca confirmada:" in rendered.conteudo


def test_prompt_template_repository_sync_default_templates_creates_new_versions(db_session):
    db_session.add(
        PromptTemplate(
            nome=PromptTemplateName.IA_OPENAI_TITLE_SYSTEM,
            conteudo="prompt legado",
            versao=1,
        )
    )
    db_session.commit()

    repository = PromptTemplateRepository(db_session)

    created_versions = repository.sync_default_templates()
    latest = repository.get_latest_template(nome=PromptTemplateName.IA_OPENAI_TITLE_SYSTEM)

    assert created_versions[PromptTemplateName.IA_OPENAI_TITLE_SYSTEM] == 2
    assert latest is not None
    assert latest.versao == 2
    assert latest.conteudo == DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_TITLE_SYSTEM]


def test_prompt_template_repository_sync_default_templates_is_idempotent_when_content_matches(db_session):
    db_session.add(
        PromptTemplate(
            nome=PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM,
            conteudo=DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM],
            versao=3,
        )
    )
    db_session.commit()

    repository = PromptTemplateRepository(db_session)

    created_versions = repository.sync_default_templates()
    matching_templates = (
        db_session.query(PromptTemplate)
        .filter(PromptTemplate.nome == PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM)
        .all()
    )

    assert PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM not in created_versions
    assert len(matching_templates) == 1


def test_prompt_template_repository_sync_default_templates_returns_empty_when_database_is_fully_synced(
    db_session,
):
    for index, (nome, conteudo) in enumerate(DEFAULT_PROMPT_TEMPLATES.items(), start=1):
        db_session.add(
            PromptTemplate(
                nome=nome,
                conteudo=conteudo,
                versao=index,
            )
        )
    db_session.commit()

    repository = PromptTemplateRepository(db_session)

    created_versions = repository.sync_default_templates()
    template_count = db_session.query(PromptTemplate).count()

    assert created_versions == {}
    assert template_count == len(DEFAULT_PROMPT_TEMPLATES)


def test_prompt_template_resolver_falls_back_when_repository_lookup_raises():
    class _BrokenSession:
        def close(self):
            return None

    class _BrokenRepository:
        def __init__(self, _db):
            pass

        def render_prompt(self, *, nome, context=None):
            _ = nome, context
            raise RuntimeError("db offline")

    resolver = PromptTemplateResolver(
        session_factory=lambda: _BrokenSession(),
        repository_cls=_BrokenRepository,
    )

    result = resolver.get_prompt(
        nome=PromptTemplateName.VALIDATOR_CREW_DESCRIPTION,
        context={"raw_data": {"sku": "1"}},
    )

    assert result.source == "default"
    assert "sku" in result.conteudo


def test_prompt_template_resolver_uses_repository_result():
    expected = PromptLookupResult(
        nome=PromptTemplateName.VALIDATOR_CREW_ROLE,
        conteudo="Role customizado",
        versao=7,
        source="database",
    )

    class _SessionStub:
        def close(self):
            return None

    class _RepositoryStub:
        def __init__(self, _db):
            pass

        def render_prompt(self, *, nome, context=None):
            assert nome == PromptTemplateName.VALIDATOR_CREW_ROLE
            assert context == {"foo": "bar"}
            return expected

    resolver = PromptTemplateResolver(
        session_factory=lambda: _SessionStub(),
        repository_cls=_RepositoryStub,
    )

    result = resolver.get_prompt(
        nome=PromptTemplateName.VALIDATOR_CREW_ROLE,
        context={"foo": "bar"},
    )

    assert result == expected
