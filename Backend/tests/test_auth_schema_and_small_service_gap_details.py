"""Targeted branch-closure tests for auth bootstrap, schemas and small backend services."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from Backend import auth as auth_module
from Backend import schemas
from Backend.application.services.fornecedor_import_tracking_service import (
    FornecedorImportTrackingService,
)
from Backend.application.services.fornecedor_management_service import (
    FornecedorManagementService,
)
from Backend.application.services.pdf_extraction_task_service import (
    PdfExtractionTaskService,
)
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository


class _FakeLogger:
    def __init__(self) -> None:
        self.warning_calls = []

    def warning(self, *args, **kwargs):
        self.warning_calls.append((args, kwargs))


def _load_auth_probe_module_with_existing_clients(monkeypatch, *, settings):
    import authlib.integrations.starlette_client as starlette_client
    import Backend.core.config as config_module
    import Backend.core.logging_config as logging_config

    logger = _FakeLogger()

    class FakeOAuth:
        def __init__(self, config=None):
            self.config = config
            self._clients = {"google": object(), "facebook": object()}
            self.register_calls = []

        def register(self, **kwargs):
            self.register_calls.append(kwargs)

    monkeypatch.setattr(config_module, "settings", settings)
    monkeypatch.setattr(logging_config, "get_logger", lambda _name: logger)
    monkeypatch.setattr(starlette_client, "OAuth", FakeOAuth)

    module_name = "Backend.tests._auth_probe_existing_clients"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, Path("Backend/auth.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, logger


def test_auth_bootstrap_skips_register_when_clients_already_exist(monkeypatch):
    settings = SimpleNamespace(
        GOOGLE_CLIENT_ID="google-id",
        GOOGLE_CLIENT_SECRET="google-secret",
        FACEBOOK_CLIENT_ID="facebook-id",
        FACEBOOK_CLIENT_SECRET="facebook-secret",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        SECRET_KEY="secret",
        REFRESH_SECRET_KEY="refresh",
        ALGORITHM="HS256",
    )

    module, logger = _load_auth_probe_module_with_existing_clients(monkeypatch, settings=settings)
    assert module.auth_config_dict_env["GOOGLE_CLIENT_ID"] == "google-id"
    assert module.auth_config_dict_env["FACEBOOK_CLIENT_ID"] == "facebook-id"
    assert module.oauth.register_calls == []
    assert logger.warning_calls == []


@pytest.mark.asyncio
async def test_auth_runtime_update_same_email_and_google_name_present_paths():
    updated = []
    current_user = SimpleNamespace(
        id=9,
        email="old@example.com",
        is_active=True,
        hashed_password="hash",
        nome_completo="Atual",
    )

    class FakeRepo:
        def get_user_by_email(self, *, email):
            return current_user if email == "new@example.com" else None

        def update_user(self, *, db_user, user_update):
            updated.append((db_user, user_update))
            return db_user

    runtime = auth_module.AuthRuntime(user_repository=FakeRepo())
    result = await runtime.update_users_me(
        user_update=schemas.UserUpdate(email="new@example.com"),
        current_user=current_user,
    )
    assert result is current_user
    assert updated

    social_calls = []

    async def _fake_get_or_create(**kwargs):
        social_calls.append(kwargs)
        return {"ok": True}

    runtime._get_or_create_social_user = _fake_get_or_create
    assert await runtime.process_google_login(
        {"email": "google@example.com", "email_verified": True, "name": "Nome Google", "sub": "gid-1"}
    ) == {"ok": True}
    assert social_calls[0]["nome"] == "Nome Google"


def test_attribute_template_options_validator_rejects_non_list_and_invalid_json():
    with pytest.raises(ValueError, match="representar uma lista"):
        schemas.AttributeTemplateBase.parse_json_options('{"a": 1}')

    with pytest.raises(ValueError, match="JSON válido"):
        schemas.AttributeTemplateBase.parse_json_options("{invalido")

    assert schemas.AttributeTemplateBase.parse_json_options(["a", "b"]) == ["a", "b"]


def test_small_services_cover_pending_status_same_name_and_count_without_filters():
    tracker = FornecedorImportTrackingService(
        models=SimpleNamespace(),
        process_pdf_extraction_task=lambda **kwargs: kwargs,
        catalog_file_repository=SimpleNamespace(get_catalog_file_for_user=lambda **kwargs: None),
    )
    assert tracker.build_import_job_status_payload(
        record=SimpleNamespace(status="PROCESSING", resultado_json={"a": 1})
    ) == {"status": "PROCESSING"}

    updated_calls = []
    service = FornecedorManagementService(
        models=SimpleNamespace(
            TipoAcaoSistemaEnum=SimpleNamespace(CRIACAO="CRIACAO", ATUALIZACAO="ATUALIZACAO", DELECAO="DELECAO")
        ),
        schemas=SimpleNamespace(RegistroHistoricoCreate=lambda **kwargs: kwargs),
        fornecedor_repo=SimpleNamespace(
            get_fornecedor=lambda **kwargs: SimpleNamespace(id=1, nome="Mesmo", user_id=7),
            update_fornecedor=lambda **kwargs: updated_calls.append(kwargs) or kwargs["db_fornecedor"],
            exists_fornecedor_with_name_for_user=lambda **kwargs: (_ for _ in ()).throw(AssertionError("nao deve validar nome")),
        ),
        historico_repo=SimpleNamespace(create_registro_historico=lambda payload: payload),
    )
    current_user = SimpleNamespace(id=7, is_superuser=False)
    updated = service.update_fornecedor(
        fornecedor_id=1,
        fornecedor_update=SimpleNamespace(nome="Mesmo"),
        current_user=current_user,
    )
    assert updated.id == 1
    assert updated_calls

    class _HistoricoQuery:
        def __init__(self):
            self.filters = []

        def filter(self, condition):
            self.filters.append(condition)
            return self

        def scalar(self):
            return 3

    class _HistoricoDb:
        def query(self, *_args):
            return _HistoricoQuery()

    assert HistoricoRepository(_HistoricoDb()).count_registros_historico() == 3


def test_pdf_extraction_task_service_handles_error_before_job_load():
    closed = []

    class _Session:
        def close(self):
            closed.append(True)

    class _Repo:
        def __init__(self, _session):
            pass

        def get_catalog_file(self, **kwargs):
            raise RuntimeError("db-fail")

    service = PdfExtractionTaskService(
        session_provider=SimpleNamespace(open_session=lambda: _Session()),
        catalog_import_file_repository_factory=_Repo,
        file_processing_service=SimpleNamespace(extract_data_from_single_page=lambda *_args, **_kwargs: {}),
    )
    service.process_pdf_extraction_task(import_job_id=1, page_number=2)
    assert closed == [True]
