"""Module test router workflows runtime basic.

Contains backend logic related to test router workflows runtime basic and documents its role in the OOP architecture.
"""

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

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_auth_workflow_get_current_user_usa_runtime_injetado():
        """Run test auth workflow get current user usa runtime injetado in this workflow."""
        called = []
    
        class FakeSecurityWorkflow:
            """Represent fake security workflow and centralize responsibilities for this module."""
            def decode_token(self, token, secret_key):
                """Run decode token in this workflow."""
                called.append(("decode", token, secret_key))
                return SimpleNamespace(user_id=123)

        class FakeUserRepository:
            """Represent fake user repository and centralize responsibilities for this module."""
            def __init__(self, db):
                """Initialize collaborators and configuration required by this component."""
                self._db = db

            def get_user(self, user_id):
                """Return user for this workflow."""
                called.append(("get_user", self._db, user_id))
                return SimpleNamespace(id=user_id, is_active=True, is_superuser=False)

        service = AuthRequestService(
            security_workflow=FakeSecurityWorkflow(),
            user_repository_factory=lambda db: FakeUserRepository(db),
        )
        user = await service.get_current_user(request=object(), session="db", token="abc")
    
        assert user.id == 123
        assert called[0][0] == "decode"
        assert called[1] == ("get_user", "db", 123)

    @pytest.mark.asyncio
    async def test_auth_workflow_get_current_user_lanca_401_quando_payload_invalido():
        """Run test auth workflow get current user lanca 401 quando payload invalido in this workflow."""
        class FakeSecurityWorkflow:
            """Represent fake security workflow and centralize responsibilities for this module."""
            def decode_token(self, token, secret_key):
                """Run decode token in this workflow."""
                return None

        class FakeUserRepository:
            """Represent fake user repository and centralize responsibilities for this module."""
            def __init__(self, db):
                """Initialize collaborators and configuration required by this component."""
                self._db = db

            def get_user(self, user_id):
                """Return user for this workflow."""
                return None

        service = AuthRequestService(
            security_workflow=FakeSecurityWorkflow(),
            user_repository_factory=lambda db: FakeUserRepository(db),
        )
    
        with pytest.raises(HTTPException) as exc_info:
            await service.get_current_user(request=object(), session="db", token="abc")
    
        assert exc_info.value.status_code == 401

    def test_historico_workflow_lista_historico_com_runtime_injetado():
        """Run test historico workflow lista historico com runtime injetado in this workflow."""
        called = []
    
        class FakeRepository:
            """Represent fake repository and centralize responsibilities for this module."""
            def get_registros_historico(self, *, user_id, skip, limit, entidade=None, acao=None):
                """Return registros historico for this workflow."""
                called.append(("items", user_id, skip, limit, entidade, acao))
                return []
    
            def count_registros_historico(self, *, user_id, entidade=None, acao=None):
                """Count registros historico for this workflow."""
                called.append(("count", user_id, entidade, acao))
                return 25

        request_service = HistoricoRequestService(session="db")
        request_service._historico_repo = FakeRepository()
        current_user = SimpleNamespace(id=77, is_superuser=False)
    
        page = request_service.list_historico(
            current_user=current_user,
            skip=10,
            limit=10,
            entidade="produto",
            acao="CRIACAO",
        )
    
        assert page.total_items == 25
        assert page.page == 2
        assert page.limit == 10
        assert called[0][0:5] == ("items", 77, 10, 10, "produto")
        assert str(called[0][5].value) == "CRIACAO"
        assert called[1][0:3] == ("count", 77, "produto")
        assert str(called[1][3].value) == "CRIACAO"

        with pytest.raises(HTTPException) as exc_info:
            request_service.list_historico(
                current_user=current_user,
                skip=0,
                limit=10,
                entidade=None,
                acao="INVALIDA",
            )

        assert exc_info.value.status_code == 422

    def test_historico_workflow_get_tipos_acao_delega_runtime():
        """Run test historico workflow get tipos acao delega runtime in this workflow."""
        response = HistoricoRequestService.get_tipos_acao()
        assert isinstance(response, list)
        assert response

    def test_search_workflow_delega_runtime_injetado():
        """Run test search workflow delega runtime injetado in this workflow."""
        now = datetime.now(timezone.utc)

        class FakeQuery:
            """Represent fake query and centralize responsibilities for this module."""
            def __init__(self, rows):
                """Initialize collaborators and configuration required by this component."""
                self._rows = rows

            def filter(self, *_args, **_kwargs):
                """Run filter in this workflow."""
                return self

            def order_by(self, *_args, **_kwargs):
                """Run order by in this workflow."""
                return self

            def limit(self, *_args, **_kwargs):
                """Run limit in this workflow."""
                return self

            def all(self):
                """Run all in this workflow."""
                return self._rows

        class FakeSession:
            """Represent fake session and centralize responsibilities for this module."""
            def __init__(self):
                """Initialize collaborators and configuration required by this component."""
                self._query_count = 0

            def query(self, *_args):
                """Run query in this workflow."""
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
        """Run test password recovery workflow recover delega runtime in this workflow."""
        called = []
    
        class FakeUserRepository:
            """Represent fake user repository and centralize responsibilities for this module."""
            def get_user_by_email(self, email):
                """Return user by email for this workflow."""
                called.append(("get_user_by_email", "db", email))
                return SimpleNamespace(email=email, nome_completo="User Test")

            def set_user_password_reset_token(self, user, *, token_hash, expires_at):
                """Run set user password reset token in this workflow."""
                called.append(("set_token", "db", user.email, token_hash, expires_at))

            def get_user_by_reset_token(self, token_hash):
                """Return user by reset token for this workflow."""
                return None

            def get_user(self, user_id):
                """Return user for this workflow."""
                return None

        class FakeAuthWorkflow:
            """Represent fake auth workflow and centralize responsibilities for this module."""
            def create_password_reset_token(self):
                """Create password reset token for this workflow."""
                called.append(("create_token",))
                return "token123"

            def hash_password_reset_token(self, token):
                """Run hash password reset token in this workflow."""
                called.append(("hash_token", token))
                return "hash123"

            def get_password_hash(self, raw_password):
                """Return password hash for this workflow."""
                return f"hashed:{raw_password}"

        class FakeEmailWorkflow:
            """Represent fake email workflow and centralize responsibilities for this module."""
            async def send_password_reset_email(self, **kwargs):
                """Run send password reset email in this workflow."""
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
        """Run test password recovery workflow reset password delega runtime e commit in this workflow."""
        class FakeDb:
            """Represent fake db and centralize responsibilities for this module."""
            def __init__(self):
                """Initialize collaborators and configuration required by this component."""
                self.committed = False
    
            def commit(self):
                """Run commit in this workflow."""
                self.committed = True
    
        class FakeAuthWorkflow:
            """Represent fake auth workflow and centralize responsibilities for this module."""
            def hash_password_reset_token(self, token):
                """Run hash password reset token in this workflow."""
                return "hash-token"

            def get_password_hash(self, raw_password):
                """Return password hash for this workflow."""
                return f"hashed:{raw_password}"

        class FakeUserRepository:
            """Represent fake user repository and centralize responsibilities for this module."""
            def get_user_by_reset_token(self, token_hash):
                """Return user by reset token for this workflow."""
                return SimpleNamespace(
                    id=42,
                    reset_password_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                )

            def get_user(self, user_id):
                """Return user for this workflow."""
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
        """Run test social auth workflow social login config delega runtime in this workflow."""
        request_service = SocialAuthRequestService(session="db")
        request_service._has_client = lambda provider: provider == "google"
        config = request_service.social_login_config()
    
        assert config.google_enabled is True
        assert config.facebook_enabled is False
        assert config.product_experience_default in {"basic", "complete"}

    @pytest.mark.asyncio
    async def test_social_auth_workflow_google_callback_delega_runtime_e_retorna_tokens():
        """Run test social auth workflow google callback delega runtime e retorna tokens in this workflow."""
        called = []
    
        class FakeAuthWorkflow:
            """Represent fake auth workflow and centralize responsibilities for this module."""
            async def process_google_login(self, google_userinfo):
                """Process google login for this workflow."""
                called.append(("process_google_login", google_userinfo))
                return SimpleNamespace(id=9, email="google@test.com")

            def create_access_token(self, payload):
                """Create access token for this workflow."""
                called.append(("create_access_token", payload))
                return "access.jwt"

            def create_refresh_token(self, payload):
                """Create refresh token for this workflow."""
                called.append(("create_refresh_token", payload))
                return "refresh.jwt"

        async def fake_authorize_access_token(provider, request):
            """Run fake authorize access token in this workflow."""
            called.append(("authorize_access_token", provider))
            return {"access": "token"}

        async def fake_parse_google_id_token(request, token):
            """Run fake parse google id token in this workflow."""
            called.append(("parse_google_id_token", token))
            return {"sub": "google-user"}

        async def fake_get_userinfo(provider, token):
            """Run fake get userinfo in this workflow."""
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
        """Run test generation workflow tarefa processar delega runtime in this workflow."""
        called = []

        class FakeTaskService:
            """Represent fake task service and centralize responsibilities for this module."""
            async def run_generation_task(self, **kwargs):
                """Run generation task for this workflow."""
                called.append(("run_generation_task", kwargs))

        request_service = GenerationRequestService(session="db")
        request_service._generation_task_service = FakeTaskService()

        await request_service.tarefa_processar_geracao_e_registrar_uso(
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
        """Run test generation workflow agendar openai titulos delega validacao e enqueue in this workflow."""
        called = []
    
        class FakeSchedulingService:
            """Represent fake scheduling service and centralize responsibilities for this module."""
            def enqueue_generation_task(self, **kwargs):
                """Run enqueue generation task in this workflow."""
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

    def test_generation_workflow_agendar_basico_descricao_delega_validacao_status_e_enqueue():
        """Run test generation workflow agendar basico descricao delega validacao status e enqueue in this workflow."""
        called = []

        class FakeSchedulingService:
            """Represent fake scheduling service and centralize responsibilities for this module."""
            def enqueue_generation_task(self, **kwargs):
                """Run enqueue generation task in this workflow."""
                called.append(("enqueue_generation_task", kwargs))

        request_service = GenerationRequestService(session="db")
        request_service._generation_scheduling_service = FakeSchedulingService()
        request_service._validate_product_access = lambda **kwargs: called.append(
            ("validate_product_access", kwargs)
        ) or SimpleNamespace(id=kwargs["produto_id"])
        request_service._mark_pending_status = lambda **kwargs: called.append(
            ("mark_pending_status", kwargs)
        )
        request_service._basic_generation_service = SimpleNamespace(
            gerar_descricao_basica="fn_basico_descricao"
        )
        user = SimpleNamespace(id=7)

        response = request_service.agendar_geracao_nova_descricao_basica(
            produto_id=31,
            background_tasks=SimpleNamespace(),
            tamanho_palavras=120,
            current_user=user,
        )

        assert "31" in response["msg"]
        assert called[0][0] == "validate_product_access"
        assert called[1][0] == "mark_pending_status"
        assert called[2][0] == "enqueue_generation_task"
        assert called[2][1]["produto_id"] == 31
        assert called[2][1]["user_id"] == 7
        assert called[2][1]["tamanho_palavras"] == 120

    @pytest.mark.asyncio
    async def test_generation_workflow_sugerir_atributos_delega_runtime():
        """Run test generation workflow sugerir atributos delega runtime in this workflow."""
        class FakeIAService:
            """Represent fake i a service and centralize responsibilities for this module."""
            async def sugerir_valores_atributos_com_gemini(self, **kwargs):
                """Run sugerir valores atributos com gemini in this workflow."""
                return {"ok": True, "produto_id": kwargs["produto_id"]}

        request_service = GenerationRequestService(session="db")
        request_service._ia_generation_service = FakeIAService()
        result = await request_service.sugerir_atributos_para_produto_com_gemini(
            produto_id=31,
            current_user=SimpleNamespace(id=5),
        )
    
        assert result == {"ok": True, "produto_id": 31}

    def test_admin_analytics_workflow_uso_ia_por_plano_delega_runtime():
        """Run test admin analytics workflow uso ia por plano delega runtime in this workflow."""
        class FakeSession:
            """Represent fake session and centralize responsibilities for this module."""
            def __init__(self):
                """Initialize collaborators and configuration required by this component."""
                self._next_counts = [7, 3]
                self._idx = 0

            def query(self, *_args):
                """Run query in this workflow."""
                parent = self

                class _CountQuery:
                    """Represent count query and centralize responsibilities for this module."""
                    def join(self, *_a, **_k):
                        """Run join in this workflow."""
                        return self

                    def filter(self, *_a, **_k):
                        """Run filter in this workflow."""
                        return self

                    def scalar(self):
                        """Run scalar in this workflow."""
                        value = parent._next_counts[parent._idx]
                        parent._idx += 1
                        return value

                return _CountQuery()

        class FakeUserRepository:
            """Represent fake user repository and centralize responsibilities for this module."""
            def get_planos(self, **kwargs):
                """Return planos for this workflow."""
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
        """Run test fornecedores workflow preview pages delega runtime in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            async def preview_pages(self, **kwargs):
                """Run preview pages in this workflow."""
                return {"ok": True, "file": kwargs["file"]}
    
        request_service = FornecedoresRequestService(runtime=FakeRuntime())
        response = await request_service.preview_pages(file="arquivo.pdf")
    
        assert response == {"ok": True, "file": "arquivo.pdf"}

    def test_product_types_workflow_read_product_types_delega_runtime():
        """Run test product types workflow read product types delega runtime in this workflow."""
        called = []
    
        class FakeRepository:
            """Represent fake repository and centralize responsibilities for this module."""
            def get_product_types_for_user(self, **kwargs):
                """Return product types for user for this workflow."""
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
        """Run test uso ia workflow create delega runtime e define user id in this workflow."""
        called = []
    
        class FakeRepository:
            """Represent fake repository and centralize responsibilities for this module."""
            def create_registro_uso_ia(self, **kwargs):
                """Create registro uso ia for this workflow."""
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
        """Run test main bootstrap workflow delega metodos sync para runtime in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def build_allowed_origins(self):
                """Build allowed origins for this workflow."""
                called.append("build_allowed_origins")
                return ["http://fake.local"]
    
            def ensure_static_files_path(self):
                """Ensure static files path for this workflow."""
                called.append("ensure_static_files_path")
                return Path("C:/tmp/static")
    
            def create_new_user(self, user_in, session):
                """Create new user for this workflow."""
                called.append(("create_new_user", user_in, session))
                return {"ok": True}
    
            async def startup_event_create_defaults(self):
                """Run startup event create defaults in this workflow."""
                called.append("startup_event_create_defaults")
    
        workflow = MainBootstrapWorkflow(runtime=FakeRuntime())
        user_payload = SimpleNamespace(email="user@test.com")
    
        assert workflow.build_allowed_origins() == ["http://fake.local"]
        assert workflow.ensure_static_files_path() == Path("C:/tmp/static")
        assert workflow.create_new_user(user_in=user_payload, session="db") == {"ok": True}
        assert called[0] == "build_allowed_origins"
        assert called[1] == "ensure_static_files_path"
        assert called[2] == ("create_new_user", user_payload, "db")

    @pytest.mark.asyncio
    async def test_main_bootstrap_workflow_delega_metodo_async_para_runtime():
        """Run test main bootstrap workflow delega metodo async para runtime in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def build_allowed_origins(self):
                """Build allowed origins for this workflow."""
                return []
    
            def ensure_static_files_path(self):
                """Ensure static files path for this workflow."""
                return Path("C:/tmp/static")
    
            def create_new_user(self, user_in, session):
                """Create new user for this workflow."""
                return None
    
            async def startup_event_create_defaults(self):
                """Run startup event create defaults in this workflow."""
                called.append("startup")
    
        workflow = MainBootstrapWorkflow(runtime=FakeRuntime())
        await workflow.startup_event_create_defaults()
        assert called == ["startup"]

    def test_produtos_workflow_runtime_override_delega_metodos_injetados():
        """Run test produtos workflow runtime override delega metodos injetados in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def create_produto(self, **kwargs):
                """Create produto for this workflow."""
                called.append(("create_produto", kwargs))
                return {"source": "runtime", "op": "create"}
    
            def list_produtos(self, **kwargs):
                """List produtos for this workflow."""
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
        """Run test produtos workflow runtime parcial preserva fallback nativo in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def create_produto(self, **kwargs):
                """Create produto for this workflow."""
                called.append(kwargs)
                return {"ok": True}

            def list_catalog_import_files(self, **kwargs):
                """List catalog import files for this workflow."""
                called.append(kwargs)
                return {"list_ok": True}
    
        workflow = ProdutosCatalogCoordinator(runtime=FakeRuntime())
        created = workflow.create_produto(
            produto=SimpleNamespace(nome_base="Teste"),
            current_user=SimpleNamespace(id=1),
        )
        assert created == {"ok": True}
        assert called[0]["produto"].nome_base == "Teste"

        response = workflow.list_catalog_import_files(
            user_id=7,
            fornecedor_id=3,
            skip=0,
            limit=10,
        )
    
        assert response == {"list_ok": True}
        assert called[1]["user_id"] == 7

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
test_generation_workflow_agendar_basico_descricao_delega_validacao_status_e_enqueue = _TopLevelFunctionSurface.test_generation_workflow_agendar_basico_descricao_delega_validacao_status_e_enqueue
































