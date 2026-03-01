from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from Backend import schemas
from Backend.main import MainBootstrapWorkflow
from Backend.routers.admin_analytics import AdminAnalyticsRequestService
from Backend.routers.auth_utils import AuthRequestService
from Backend.routers.fornecedores import FornecedoresRequestService
from Backend.routers.generation import GenerationRequestService
from Backend.routers.historico import HistoricoRequestService
from Backend.routers.password_recovery import PasswordRecoveryRequestService
from Backend.routers.product_types import ProductTypesRequestService
from Backend.routers.produtos import ProdutosCatalogCoordinator
from Backend.routers.search import SearchRequestService
from Backend.routers.social_auth import SocialAuthRequestService
from Backend.routers.uso_ia import UsoIARequestService


class _TopLevelFunctionSurface:

    @pytest.mark.asyncio
    async def test_auth_workflow_get_current_user_usa_runtime_injetado():
        called = []
    
        class FakeSecurityWorkflow:
            def decode_token(self, token, secret_key):
                called.append(("decode", token, secret_key))
                return SimpleNamespace(user_id=123)

        class FakeUserRepository:
            def __init__(self, db):
                self._db = db

            def get_user(self, user_id):
                called.append(("get_user", self._db, user_id))
                return SimpleNamespace(id=user_id, is_active=True, is_superuser=False)

        service = AuthRequestService(
            security_workflow=FakeSecurityWorkflow(),
            user_repository_cls=FakeUserRepository,
        )
        user = await service.get_current_user(request=object(), session="db", token="abc")
    
        assert user.id == 123
        assert called[0][0] == "decode"
        assert called[1] == ("get_user", "db", 123)

    @pytest.mark.asyncio
    async def test_auth_workflow_get_current_user_lanca_401_quando_payload_invalido():
        class FakeSecurityWorkflow:
            def decode_token(self, token, secret_key):
                return None

        class FakeUserRepository:
            def __init__(self, db):
                self._db = db

            def get_user(self, user_id):
                return None

        service = AuthRequestService(
            security_workflow=FakeSecurityWorkflow(),
            user_repository_cls=FakeUserRepository,
        )
    
        with pytest.raises(HTTPException) as exc_info:
            await service.get_current_user(request=object(), session="db", token="abc")
    
        assert exc_info.value.status_code == 401

    def test_historico_workflow_lista_historico_com_runtime_injetado():
        called = []
    
        class FakeRepository:
            def get_registros_historico(self, *, user_id, skip, limit):
                called.append(("items", user_id, skip, limit))
                return []
    
            def count_registros_historico(self, *, user_id):
                called.append(("count", user_id))
                return 25

        request_service = HistoricoRequestService(session="db")
        request_service._historico_repo = FakeRepository()
        current_user = SimpleNamespace(id=77, is_superuser=False)
    
        page = request_service.list_historico(current_user=current_user, skip=10, limit=10)
    
        assert page.total_items == 25
        assert page.page == 2
        assert page.limit == 10
        assert called[0] == ("items", 77, 10, 10)
        assert called[1] == ("count", 77)

    def test_historico_workflow_get_tipos_acao_delega_runtime():
        response = HistoricoRequestService.get_tipos_acao()
        assert isinstance(response, list)
        assert response

    def test_search_workflow_delega_runtime_injetado():
        now = datetime.now(timezone.utc)

        class FakeQuery:
            def __init__(self, rows):
                self._rows = rows

            def filter(self, *_args, **_kwargs):
                return self

            def order_by(self, *_args, **_kwargs):
                return self

            def limit(self, *_args, **_kwargs):
                return self

            def all(self):
                return self._rows

        class FakeSession:
            def __init__(self):
                self._query_count = 0

            def query(self, *_args):
                self._query_count += 1
                if self._query_count == 1:
                    return FakeQuery(
                        [SimpleNamespace(id=1, nome_base="Produto X", created_at=now)]
                    )
                if self._query_count == 2:
                    return FakeQuery(
                        [SimpleNamespace(id=2, nome="Fornecedor Y", created_at=now)]
                    )
                return FakeQuery(
                    [SimpleNamespace(id=3, friendly_name="Tipo Z", created_at=now)]
                )

        request_service = SearchRequestService(session=FakeSession())
        result = request_service.search_all(
            current_user=SimpleNamespace(id=1, is_superuser=False),
            q="abc",
            limit=5,
        )
    
        assert len(result.results) == 3
        assert {item.type for item in result.results} == {
            "produto",
            "fornecedor",
            "tipo_produto",
        }

    @pytest.mark.asyncio
    async def test_password_recovery_workflow_recover_delega_runtime():
        called = []
    
        class FakeUserRepository:
            def get_user_by_email(self, email):
                called.append(("get_user_by_email", "db", email))
                return SimpleNamespace(email=email, nome_completo="User Test")

            def set_user_password_reset_token(self, user, *, token_hash, expires_at):
                called.append(("set_token", "db", user.email, token_hash, expires_at))

            def get_user_by_reset_token(self, token_hash):
                return None

            def get_user(self, user_id):
                return None

        class FakeAuthWorkflow:
            def create_password_reset_token(self):
                called.append(("create_token",))
                return "token123"

            def hash_password_reset_token(self, token):
                called.append(("hash_token", token))
                return "hash123"

            def get_password_hash(self, raw_password):
                return f"hashed:{raw_password}"

        class FakeEmailWorkflow:
            async def send_password_reset_email(self, **kwargs):
                called.append(("send_email", kwargs))

        service = PasswordRecoveryRequestService(session="db")
        service._user_repository = FakeUserRepository()
        service._auth_workflow = FakeAuthWorkflow()
        service._email_workflow = FakeEmailWorkflow()
        response = await service.recover_password(email="user@test.com", request=object())
    
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
    
        class FakeAuthWorkflow:
            def hash_password_reset_token(self, token):
                return "hash-token"

            def get_password_hash(self, raw_password):
                return f"hashed:{raw_password}"

        class FakeUserRepository:
            def get_user_by_reset_token(self, token_hash):
                return SimpleNamespace(
                    id=42,
                    reset_password_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                )

            def get_user(self, user_id):
                return SimpleNamespace(
                    id=user_id,
                    hashed_password=None,
                    reset_password_token="hash-token",
                    reset_password_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                )

        service = PasswordRecoveryRequestService(session=FakeDb())
        service._auth_workflow = FakeAuthWorkflow()
        service._user_repository = FakeUserRepository()
        db = FakeDb()
        service._session = db
        reset_data = schemas.PasswordResetSchema(token="abc", new_password="NovaSenha123!")
    
        response = service.reset_password(reset_data=reset_data)
    
        assert response.msg == "Senha atualizada com sucesso."
        assert db.committed is True

    def test_social_auth_workflow_social_login_config_delega_runtime():
        request_service = SocialAuthRequestService(session="db")
        request_service._has_client = lambda provider: provider == "google"
        config = request_service.social_login_config()
    
        assert config.google_enabled is True
        assert config.facebook_enabled is False

    @pytest.mark.asyncio
    async def test_social_auth_workflow_google_callback_delega_runtime_e_retorna_tokens():
        called = []
    
        class FakeAuthWorkflow:
            async def process_google_login(self, db, google_userinfo):
                called.append(("process_google_login", db, google_userinfo))
                return SimpleNamespace(id=9, email="google@test.com")

            def create_access_token(self, payload):
                called.append(("create_access_token", payload))
                return "access.jwt"

            def create_refresh_token(self, payload):
                called.append(("create_refresh_token", payload))
                return "refresh.jwt"

        async def fake_authorize_access_token(provider, request):
            called.append(("authorize_access_token", provider))
            return {"access": "token"}

        async def fake_parse_google_id_token(request, token):
            called.append(("parse_google_id_token", token))
            return {"sub": "google-user"}

        async def fake_get_userinfo(provider, token):
            called.append(("get_userinfo", provider))
            return {"sub": "fallback"}

        request_service = SocialAuthRequestService(session="db")
        request_service._auth_workflow = FakeAuthWorkflow()
        request_service._has_client = lambda provider: True
        request_service._authorize_access_token = fake_authorize_access_token
        request_service._parse_google_id_token = fake_parse_google_id_token
        request_service._get_userinfo = fake_get_userinfo

        token = await request_service.google_callback(request=object())

        assert token.access_token == "access.jwt"
        assert token.token_type == "bearer"
        assert called[0] == ("authorize_access_token", "google")
        assert called[1][0] == "parse_google_id_token"
        assert called[2][0] == "process_google_login"
        assert called[4][0] == "create_refresh_token"

    @pytest.mark.asyncio
    async def test_generation_workflow_tarefa_processar_delega_runtime():
        called = []

        class FakeTaskService:
            async def run_generation_task(self, **kwargs):
                called.append(("run_generation_task", kwargs))

        request_service = GenerationRequestService(session="db")
        request_service._generation_task_service = FakeTaskService()

        await request_service.tarefa_processar_geracao_e_registrar_uso(
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
    
        class FakeSchedulingService:
            def enqueue_generation_task(self, **kwargs):
                called.append(("enqueue_generation_task", kwargs))

        request_service = GenerationRequestService(session="db")
        request_service._generation_scheduling_service = FakeSchedulingService()
        request_service._validate_product_access = lambda **kwargs: called.append(
            ("validate_product_access", kwargs)
        ) or SimpleNamespace(id=kwargs["produto_id"])
        request_service._ia_generation_service = SimpleNamespace(
            gerar_titulos_com_openai="fn_openai"
        )
        user = SimpleNamespace(id=4)
    
        response = request_service.agendar_geracao_novos_titulos_openai(
            produto_id=22,
            background_tasks=SimpleNamespace(),
            num_titulos=5,
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
        class FakeIAService:
            async def sugerir_valores_atributos_com_gemini(self, **kwargs):
                return {"ok": True, "produto_id": kwargs["produto_id"]}

        request_service = GenerationRequestService(session="db")
        request_service._ia_generation_service = FakeIAService()
        result = await request_service.sugerir_atributos_para_produto_com_gemini(
            produto_id=31,
            current_user=SimpleNamespace(id=5),
        )
    
        assert result == {"ok": True, "produto_id": 31}

    def test_admin_analytics_workflow_uso_ia_por_plano_delega_runtime():
        class FakeSession:
            def __init__(self):
                self._next_counts = [7, 3]
                self._idx = 0

            def query(self, *_args):
                parent = self

                class _CountQuery:
                    def join(self, *_a, **_k):
                        return self

                    def filter(self, *_a, **_k):
                        return self

                    def scalar(self):
                        value = parent._next_counts[parent._idx]
                        parent._idx += 1
                        return value

                return _CountQuery()

        class FakeUserRepository:
            def get_planos(self, **kwargs):
                return [SimpleNamespace(id=1, nome="Pro"), SimpleNamespace(id=2, nome="Free")]

        request_service = AdminAnalyticsRequestService(session=FakeSession())
        request_service._user_repository = FakeUserRepository()
        request_service._now_utc = lambda: datetime(2026, 2, 10, tzinfo=timezone.utc)
        result = request_service.get_uso_ia_por_plano()
    
        assert len(result) == 2
        assert result[0].total_geracoes_ia_no_mes == 7
        assert result[1].total_geracoes_ia_no_mes == 3

    @pytest.mark.asyncio
    async def test_fornecedores_workflow_preview_pages_delega_runtime():
        class FakeRuntime:
            async def preview_pages(self, **kwargs):
                return {"ok": True, "file": kwargs["file"]}
    
        request_service = FornecedoresRequestService(runtime=FakeRuntime())
        response = await request_service.preview_pages(file="arquivo.pdf")
    
        assert response == {"ok": True, "file": "arquivo.pdf"}

    def test_product_types_workflow_read_product_types_delega_runtime():
        called = []
    
        class FakeRepository:
            def get_product_types_for_user(self, **kwargs):
                called.append(kwargs)
                return [SimpleNamespace(id=1, key_name="auto")]

        request_service = ProductTypesRequestService(session="db")
        request_service._product_type_repo = FakeRepository()
        user = SimpleNamespace(id=9)
        result = request_service.read_product_types(current_user=user, skip=5, limit=20)
    
        assert len(result) == 1
        assert called[0]["user_id"] == 9
        assert called[0]["skip"] == 5
        assert called[0]["limit"] == 20

    def test_uso_ia_workflow_create_delega_runtime_e_define_user_id():
        called = []
    
        class FakeRepository:
            def create_registro_uso_ia(self, **kwargs):
                called.append(kwargs)
                return {"id": 123}

        request_service = UsoIARequestService(session="db")
        request_service._registro_repo = FakeRepository()
        payload = schemas.RegistroUsoIACreate(
            user_id=0,
            produto_id=11,
            tipo_acao=schemas.TipoAcaoEnum.CRIACAO_PRODUTO,
            modelo_ia="gemini-1.5-flash",
            creditos_consumidos=1,
        )
        response = request_service.create_uso_ia(
            current_user=SimpleNamespace(id=77),
            uso_ia_data=payload,
        )
    
        assert response == {"id": 123}
        assert payload.user_id == 77
        assert called[0]["registro_uso"].user_id == 77

    def test_main_bootstrap_workflow_delega_metodos_sync_para_runtime():
        called = []
    
        class FakeRuntime:
            def build_allowed_origins(self):
                called.append("build_allowed_origins")
                return ["http://fake.local"]
    
            def ensure_static_files_path(self):
                called.append("ensure_static_files_path")
                return Path("C:/tmp/static")
    
            def create_new_user(self, user_in, db):
                called.append(("create_new_user", user_in, db))
                return {"ok": True}
    
            async def startup_event_create_defaults(self):
                called.append("startup_event_create_defaults")
    
        workflow = MainBootstrapWorkflow(runtime=FakeRuntime())
        user_payload = SimpleNamespace(email="user@test.com")
    
        assert workflow.build_allowed_origins() == ["http://fake.local"]
        assert workflow.ensure_static_files_path() == Path("C:/tmp/static")
        assert workflow.create_new_user(user_in=user_payload, db="db") == {"ok": True}
        assert called[0] == "build_allowed_origins"
        assert called[1] == "ensure_static_files_path"
        assert called[2] == ("create_new_user", user_payload, "db")

    @pytest.mark.asyncio
    async def test_main_bootstrap_workflow_delega_metodo_async_para_runtime():
        called = []
    
        class FakeRuntime:
            def build_allowed_origins(self):
                return []
    
            def ensure_static_files_path(self):
                return Path("C:/tmp/static")
    
            def create_new_user(self, user_in, db):
                return None
    
            async def startup_event_create_defaults(self):
                called.append("startup")
    
        workflow = MainBootstrapWorkflow(runtime=FakeRuntime())
        await workflow.startup_event_create_defaults()
        assert called == ["startup"]

    def test_produtos_workflow_runtime_override_delega_metodos_injetados():
        called = []
    
        class FakeRuntime:
            def create_produto(self, **kwargs):
                called.append(("create_produto", kwargs))
                return {"source": "runtime", "op": "create"}
    
            def list_produtos(self, **kwargs):
                called.append(("list_produtos", kwargs))
                return {"source": "runtime", "op": "list"}
    
        workflow = ProdutosCatalogCoordinator(runtime=FakeRuntime())
    
        created = workflow.create_produto(
            produto=SimpleNamespace(nome_base="x"),
            current_user=SimpleNamespace(id=1),
        )
        listed = workflow.list_produtos(
            skip=0,
            limit=10,
            sort_by=None,
            sort_order="asc",
            search=None,
            fornecedor_id=None,
            categoria=None,
            status_enriquecimento_web=None,
            status_titulo_ia=None,
            status_descricao_ia=None,
            product_type_id=None,
            current_user=SimpleNamespace(id=1),
        )
    
        assert created["source"] == "runtime"
        assert listed["source"] == "runtime"
        assert called[0][0] == "create_produto"
        assert called[1][0] == "list_produtos"

    def test_produtos_workflow_runtime_parcial_preserva_fallback_nativo():
        called = []
    
        class FakeRuntime:
            def create_produto(self, **kwargs):
                called.append(kwargs)
                return {"ok": True}
    
        workflow = ProdutosCatalogCoordinator(runtime=FakeRuntime())
        created = workflow.create_produto(
            produto=SimpleNamespace(nome_base="Teste"),
            current_user=SimpleNamespace(id=1),
        )
        assert created == {"ok": True}
        assert called[0]["produto"].nome_base == "Teste"
    
        fallback_called = []
    
        class FakeDefaultRuntime:
            def list_catalog_import_files(self, **kwargs):
                fallback_called.append(kwargs)
                return {"fallback": True}
    
        workflow.set_default_runtime(FakeDefaultRuntime())
        response = workflow.list_catalog_import_files(
            user_id=7,
            fornecedor_id=3,
            skip=0,
            limit=10,
        )
    
        assert response == {"fallback": True}
        assert fallback_called[0]["user_id"] == 7

test_auth_workflow_get_current_user_usa_runtime_injetado = _TopLevelFunctionSurface.test_auth_workflow_get_current_user_usa_runtime_injetado
test_auth_workflow_get_current_user_lanca_401_quando_payload_invalido = _TopLevelFunctionSurface.test_auth_workflow_get_current_user_lanca_401_quando_payload_invalido
test_historico_workflow_lista_historico_com_runtime_injetado = _TopLevelFunctionSurface.test_historico_workflow_lista_historico_com_runtime_injetado
test_historico_workflow_get_tipos_acao_delega_runtime = _TopLevelFunctionSurface.test_historico_workflow_get_tipos_acao_delega_runtime
test_search_workflow_delega_runtime_injetado = _TopLevelFunctionSurface.test_search_workflow_delega_runtime_injetado
test_password_recovery_workflow_recover_delega_runtime = _TopLevelFunctionSurface.test_password_recovery_workflow_recover_delega_runtime
test_password_recovery_workflow_reset_password_delega_runtime_e_commit = _TopLevelFunctionSurface.test_password_recovery_workflow_reset_password_delega_runtime_e_commit
test_social_auth_workflow_social_login_config_delega_runtime = _TopLevelFunctionSurface.test_social_auth_workflow_social_login_config_delega_runtime
test_social_auth_workflow_google_callback_delega_runtime_e_retorna_tokens = _TopLevelFunctionSurface.test_social_auth_workflow_google_callback_delega_runtime_e_retorna_tokens
test_generation_workflow_tarefa_processar_delega_runtime = _TopLevelFunctionSurface.test_generation_workflow_tarefa_processar_delega_runtime
test_generation_workflow_agendar_openai_titulos_delega_validacao_e_enqueue = _TopLevelFunctionSurface.test_generation_workflow_agendar_openai_titulos_delega_validacao_e_enqueue
test_generation_workflow_sugerir_atributos_delega_runtime = _TopLevelFunctionSurface.test_generation_workflow_sugerir_atributos_delega_runtime
test_admin_analytics_workflow_uso_ia_por_plano_delega_runtime = _TopLevelFunctionSurface.test_admin_analytics_workflow_uso_ia_por_plano_delega_runtime
test_fornecedores_workflow_preview_pages_delega_runtime = _TopLevelFunctionSurface.test_fornecedores_workflow_preview_pages_delega_runtime
test_product_types_workflow_read_product_types_delega_runtime = _TopLevelFunctionSurface.test_product_types_workflow_read_product_types_delega_runtime
test_uso_ia_workflow_create_delega_runtime_e_define_user_id = _TopLevelFunctionSurface.test_uso_ia_workflow_create_delega_runtime_e_define_user_id
test_main_bootstrap_workflow_delega_metodos_sync_para_runtime = _TopLevelFunctionSurface.test_main_bootstrap_workflow_delega_metodos_sync_para_runtime
test_main_bootstrap_workflow_delega_metodo_async_para_runtime = _TopLevelFunctionSurface.test_main_bootstrap_workflow_delega_metodo_async_para_runtime
test_produtos_workflow_runtime_override_delega_metodos_injetados = _TopLevelFunctionSurface.test_produtos_workflow_runtime_override_delega_metodos_injetados
test_produtos_workflow_runtime_parcial_preserva_fallback_nativo = _TopLevelFunctionSurface.test_produtos_workflow_runtime_parcial_preserva_fallback_nativo
































