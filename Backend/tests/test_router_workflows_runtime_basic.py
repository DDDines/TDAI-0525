from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from Backend import schemas
from Backend.routers.auth_utils import _AuthUtilsWorkflow
from Backend.routers.generation import _GenerationRouterWorkflow
from Backend.routers.historico import _HistoricoWorkflow
from Backend.routers.password_recovery import _PasswordRecoveryWorkflow
from Backend.routers.search import _SearchWorkflow
from Backend.routers.social_auth import _SocialAuthRouterWorkflow


@pytest.mark.asyncio
async def test_auth_workflow_get_current_user_usa_runtime_injetado():
    called = []

    class FakeRuntime:
        def decode_token(self, token, secret_key):
            called.append(("decode", token, secret_key))
            return SimpleNamespace(user_id=123)

        def get_user(self, db, user_id):
            called.append(("get_user", db, user_id))
            return SimpleNamespace(id=user_id, is_active=True, is_superuser=False)

    workflow = _AuthUtilsWorkflow(runtime=FakeRuntime())
    user = await workflow.get_current_user(request=object(), db="db", token="abc")

    assert user.id == 123
    assert called[0][0] == "decode"
    assert called[1] == ("get_user", "db", 123)


@pytest.mark.asyncio
async def test_auth_workflow_get_current_user_lanca_401_quando_payload_invalido():
    class FakeRuntime:
        def decode_token(self, token, secret_key):
            return None

        def get_user(self, db, user_id):
            return None

    workflow = _AuthUtilsWorkflow(runtime=FakeRuntime())

    with pytest.raises(HTTPException) as exc_info:
        await workflow.get_current_user(request=object(), db="db", token="abc")

    assert exc_info.value.status_code == 401


def test_historico_workflow_lista_historico_com_runtime_injetado():
    called = []

    class FakeRuntime:
        def get_registros_historico(self, db, *, user_id, skip, limit):
            called.append(("items", db, user_id, skip, limit))
            return []

        def count_registros_historico(self, db, *, user_id):
            called.append(("count", db, user_id))
            return 25

        def get_tipos_acao(self):
            called.append(("tipos",))
            return ["CRIACAO", "ATUALIZACAO"]

    workflow = _HistoricoWorkflow(runtime=FakeRuntime())
    current_user = SimpleNamespace(id=77, is_superuser=False)

    page = workflow.list_historico(db="db", current_user=current_user, skip=10, limit=10)

    assert page.total_items == 25
    assert page.page == 2
    assert page.limit == 10
    assert called[0] == ("items", "db", 77, 10, 10)
    assert called[1] == ("count", "db", 77)


def test_historico_workflow_get_tipos_acao_delega_runtime():
    class FakeRuntime:
        def get_registros_historico(self, db, *, user_id, skip, limit):
            return []

        def count_registros_historico(self, db, *, user_id):
            return 0

        def get_tipos_acao(self):
            return ["CRIACAO", "DELECAO"]

    workflow = _HistoricoWorkflow(runtime=FakeRuntime())
    assert workflow.get_tipos_acao() == ["CRIACAO", "DELECAO"]


def test_search_workflow_delega_runtime_injetado():
    called = []

    class FakeRuntime:
        def search_all(self, **kwargs):
            called.append(kwargs)
            return {"ok": True}

    workflow = _SearchWorkflow(runtime=FakeRuntime())
    result = workflow.search_all(
        db="db",
        current_user=SimpleNamespace(id=1),
        q="abc",
        limit=5,
    )

    assert result == {"ok": True}
    assert called[0]["db"] == "db"
    assert called[0]["q"] == "abc"
    assert called[0]["limit"] == 5


@pytest.mark.asyncio
async def test_password_recovery_workflow_recover_delega_runtime():
    called = []

    class FakeRuntime:
        def get_user_by_email(self, db, email):
            called.append(("get_user_by_email", db, email))
            return SimpleNamespace(email=email, nome_completo="User Test")

        def create_password_reset_token(self):
            called.append(("create_token",))
            return "token123"

        def hash_password_reset_token(self, token):
            called.append(("hash_token", token))
            return "hash123"

        def set_user_password_reset_token(self, db, user, *, token_hash, expires_at):
            called.append(("set_token", db, user.email, token_hash, expires_at))

        async def send_password_reset_email(self, **kwargs):
            called.append(("send_email", kwargs))

        def get_user_by_reset_token(self, db, token_hash):
            return None

        def get_user(self, db, user_id):
            return None

        def get_password_hash(self, raw_password):
            return f"hashed:{raw_password}"

    workflow = _PasswordRecoveryWorkflow(runtime=FakeRuntime())
    response = await workflow.recover_password(db="db", email="user@test.com", request=object())

    assert response.msg == "Email de recuperacao de senha enviado com sucesso."
    assert called[0] == ("get_user_by_email", "db", "user@test.com")
    assert called[1] == ("create_token",)
    assert called[2] == ("hash_token", "token123")
    assert called[3][0] == "set_token"
    assert called[4][0] == "send_email"


def test_password_recovery_workflow_reset_password_delega_runtime_e_commit():
    class FakeDb:
        def __init__(self):
            self.committed = False

        def commit(self):
            self.committed = True

    class FakeRuntime:
        def hash_password_reset_token(self, token):
            return "hash-token"

        def get_user_by_reset_token(self, db, token_hash):
            return SimpleNamespace(
                id=42,
                reset_password_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )

        def get_user(self, db, user_id):
            return SimpleNamespace(
                id=user_id,
                hashed_password=None,
                reset_password_token="hash-token",
                reset_password_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )

        def get_password_hash(self, raw_password):
            return f"hashed:{raw_password}"

        def get_user_by_email(self, db, email):
            return None

        def create_password_reset_token(self):
            return "token"

        def set_user_password_reset_token(self, db, user, *, token_hash, expires_at):
            return None

        async def send_password_reset_email(self, **kwargs):
            return None

    workflow = _PasswordRecoveryWorkflow(runtime=FakeRuntime())
    db = FakeDb()
    reset_data = schemas.PasswordResetSchema(token="abc", new_password="NovaSenha123!")

    response = workflow.reset_password(db=db, reset_data=reset_data)

    assert response.msg == "Senha atualizada com sucesso."
    assert db.committed is True


def test_social_auth_workflow_social_login_config_delega_runtime():
    class FakeRuntime:
        def has_client(self, provider):
            return provider == "google"

    workflow = _SocialAuthRouterWorkflow(runtime=FakeRuntime())
    config = workflow.social_login_config()

    assert config.google_enabled is True
    assert config.facebook_enabled is False


@pytest.mark.asyncio
async def test_social_auth_workflow_google_callback_delega_runtime_e_retorna_tokens():
    called = []

    class FakeRuntime:
        def has_client(self, provider):
            return True

        async def authorize_access_token(self, provider, request):
            called.append(("authorize_access_token", provider))
            return {"access": "token"}

        async def parse_google_id_token(self, request, token):
            called.append(("parse_google_id_token", token))
            return {"sub": "google-user"}

        async def get_userinfo(self, provider, token):
            called.append(("get_userinfo", provider))
            return {"sub": "fallback"}

        async def process_google_login(self, db, userinfo):
            called.append(("process_google_login", db, userinfo))
            return SimpleNamespace(id=9, email="google@test.com")

        def create_access_token(self, payload):
            called.append(("create_access_token", payload))
            return "access.jwt"

        def create_refresh_token(self, payload):
            called.append(("create_refresh_token", payload))
            return "refresh.jwt"

        async def authorize_redirect(self, provider, request, redirect_uri):
            return "redirect"

        async def process_facebook_login(self, db, userinfo):
            return None

    workflow = _SocialAuthRouterWorkflow(runtime=FakeRuntime())
    token = await workflow.google_callback(request=object(), db="db")

    assert token.access_token == "access.jwt"
    assert token.token_type == "bearer"
    assert called[0] == ("authorize_access_token", "google")
    assert called[1][0] == "parse_google_id_token"
    assert called[2][0] == "process_google_login"
    assert called[4][0] == "create_refresh_token"


@pytest.mark.asyncio
async def test_generation_workflow_tarefa_processar_delega_runtime():
    called = []

    class FakeRuntime:
        async def run_generation_task(self, **kwargs):
            called.append(("run_generation_task", kwargs))

        def validate_product_access(self, **kwargs):
            called.append(("validate_product_access", kwargs))
            return SimpleNamespace(id=kwargs["produto_id"])

        def mark_pending_status(self, **kwargs):
            called.append(("mark_pending_status", kwargs))

        def enqueue_generation_task(self, **kwargs):
            called.append(("enqueue_generation_task", kwargs))

        async def sugerir_valores_atributos_com_gemini(self, **kwargs):
            called.append(("sugerir_valores_atributos_com_gemini", kwargs))
            return {"ok": True}

    workflow = _GenerationRouterWorkflow(runtime=FakeRuntime())

    await workflow.tarefa_processar_geracao_e_registrar_uso(
        db_session_factory="db_factory",
        user_id=7,
        produto_id=9,
        tipo_geracao_principal="titulo",
        funcao_geracao_ia_no_servico="fn",
        num_titulos=3,
    )

    assert called[0][0] == "run_generation_task"
    assert called[0][1]["produto_id"] == 9
    assert called[0][1]["num_titulos"] == 3


def test_generation_workflow_agendar_openai_titulos_delega_validacao_e_enqueue():
    called = []

    class FakeRuntime:
        async def run_generation_task(self, **kwargs):
            called.append(("run_generation_task", kwargs))

        def validate_product_access(self, **kwargs):
            called.append(("validate_product_access", kwargs))
            return SimpleNamespace(id=kwargs["produto_id"])

        def mark_pending_status(self, **kwargs):
            called.append(("mark_pending_status", kwargs))

        def enqueue_generation_task(self, **kwargs):
            called.append(("enqueue_generation_task", kwargs))

        async def sugerir_valores_atributos_com_gemini(self, **kwargs):
            called.append(("sugerir_valores_atributos_com_gemini", kwargs))
            return {"ok": True}

    workflow = _GenerationRouterWorkflow(runtime=FakeRuntime())
    user = SimpleNamespace(id=4)

    response = workflow.agendar_geracao_novos_titulos_openai(
        produto_id=22,
        background_tasks=SimpleNamespace(),
        num_titulos=5,
        db="db",
        current_user=user,
    )

    assert "22" in response["msg"]
    assert called[0][0] == "validate_product_access"
    assert called[1][0] == "enqueue_generation_task"
    assert called[1][1]["produto_id"] == 22
    assert called[1][1]["user_id"] == 4
    assert called[1][1]["num_titulos"] == 5


@pytest.mark.asyncio
async def test_generation_workflow_sugerir_atributos_delega_runtime():
    class FakeRuntime:
        async def run_generation_task(self, **kwargs):
            return None

        def validate_product_access(self, **kwargs):
            return SimpleNamespace(id=kwargs["produto_id"])

        def mark_pending_status(self, **kwargs):
            return None

        def enqueue_generation_task(self, **kwargs):
            return None

        async def sugerir_valores_atributos_com_gemini(self, **kwargs):
            return {"ok": True, "produto_id": kwargs["produto_id"]}

    workflow = _GenerationRouterWorkflow(runtime=FakeRuntime())
    result = await workflow.sugerir_atributos_para_produto_com_gemini(
        produto_id=31,
        db="db",
        current_user=SimpleNamespace(id=5),
    )

    assert result == {"ok": True, "produto_id": 31}
