"""Targeted coverage for the persisted basic template router."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import models
from Backend.routers import basic_templates as basic_templates_module


class _FakeRepository:
    def __init__(self, session):
        self.session = session
        self.calls = []
        self.deleted = True

    def build_overview(self, *, current_user):
        self.calls.append(("build_overview", current_user.id))
        return {
            "company_identifier": current_user.company_identifier,
            "company_config": None,
            "user_config": None,
            "effective_config": {
                "source": "system",
                "source_label": "Sistema",
                "title_template": "{titulo_base}",
                "description_template": "{nome_base}",
                "is_custom": False,
            },
            "system_defaults": {
                "title_template": "{titulo_base}",
                "description_template": "{nome_base}",
            },
        }

    def upsert_config(self, **kwargs):
        self.calls.append(("upsert_config", kwargs))
        return SimpleNamespace(
            id=7,
            scope_type=kwargs["scope_type"],
            title_template=kwargs["title_template"],
            description_template=kwargs["description_template"],
            is_active=kwargs["is_active"],
            created_at=None,
            updated_at=None,
        )

    def serialize_config(self, config):
        self.calls.append(("serialize_config", config.id))
        return {
            "id": config.id,
            "scope_type": config.scope_type,
            "title_template": config.title_template,
            "description_template": config.description_template,
            "is_active": config.is_active,
            "source_label": "Pessoal",
            "created_at": None,
            "updated_at": None,
        }

    def delete_config(self, **kwargs):
        self.calls.append(("delete_config", kwargs))
        return self.deleted


def _current_user(*, is_superuser=False, role_name="user"):
    return SimpleNamespace(
        id=11,
        is_superuser=is_superuser,
        role=SimpleNamespace(name=role_name),
        company_identifier="catalog-ai-ltda",
    )


def test_basic_templates_overview_delegates_to_repository(monkeypatch):
    created = []

    def _factory(session):
        repo = _FakeRepository(session)
        created.append(repo)
        return repo

    monkeypatch.setattr(basic_templates_module, "BasicGenerationTemplateRepository", _factory)

    response = basic_templates_module.read_basic_generation_templates_overview(
        current_user=_current_user(),
        session="db",
    )

    assert response["effective_config"]["source"] == "system"
    assert created[0].calls == [("build_overview", 11)]


def test_basic_templates_upsert_blocks_company_scope_for_non_admin(monkeypatch):
    monkeypatch.setattr(
        basic_templates_module,
        "BasicGenerationTemplateRepository",
        lambda session: _FakeRepository(session),
    )

    payload = SimpleNamespace(
        scope_type=models.ExternalCredentialScopeEnum.COMPANY,
        title_template="{titulo_base}",
        description_template="{nome_base}",
        is_active=True,
    )

    with pytest.raises(HTTPException, match="Somente administradores"):
        basic_templates_module.upsert_basic_generation_templates(
            payload=payload,
            current_user=_current_user(),
            session="db",
        )


def test_basic_templates_upsert_and_delete_delegate_to_repository(monkeypatch):
    repo = _FakeRepository(session="db")
    monkeypatch.setattr(
        basic_templates_module,
        "BasicGenerationTemplateRepository",
        lambda session: repo,
    )

    payload = SimpleNamespace(
        scope_type=models.ExternalCredentialScopeEnum.USER,
        title_template="{titulo_base} {reference}",
        description_template="{nome_base}\n{specs}",
        is_active=True,
    )

    response = basic_templates_module.upsert_basic_generation_templates(
        payload=payload,
        current_user=_current_user(is_superuser=True),
        session="db",
    )
    assert response["title_template"] == "{titulo_base} {reference}"

    delete_response = basic_templates_module.delete_basic_generation_templates(
        scope_type=models.ExternalCredentialScopeEnum.USER,
        current_user=_current_user(is_superuser=True),
        session="db",
    )
    assert delete_response.msg == "Template básico removido com sucesso."

    repo.deleted = False
    with pytest.raises(HTTPException, match="Template básico não encontrado."):
        basic_templates_module.delete_basic_generation_templates(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            current_user=_current_user(is_superuser=True),
            session="db",
        )
