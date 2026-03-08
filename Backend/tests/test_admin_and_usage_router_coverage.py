"""Coverage for admin analytics and IA usage request services and route wrappers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import models, schemas
from Backend.routers import admin_analytics as admin_router
from Backend.routers import uso_ia as uso_ia_router
from Backend.routers.admin_analytics import AdminAnalyticsRequestService
from Backend.routers.uso_ia import UsoIARequestService


def _uso_payload() -> schemas.RegistroUsoIACreate:
    return schemas.RegistroUsoIACreate(
        user_id=0,
        produto_id=11,
        tipo_acao=schemas.TipoAcaoEnum.CRIACAO_PRODUTO,
        modelo_ia="gemini-1.5-flash",
        creditos_consumidos=1,
    )


def _uso_response_item(record_id: int = 1):
    return SimpleNamespace(
        id=record_id,
        user_id=7,
        produto_id=11,
        tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO,
        provedor_ia="gemini",
        modelo_ia="gemini-1.5-flash",
        prompt_utilizado=None,
        resposta_ia=None,
        tokens_prompt=None,
        tokens_resposta=None,
        custo_estimado_usd=None,
        creditos_consumidos=1,
        status="SUCESSO",
        detalhes_erro=None,
        created_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
    )


def test_uso_ia_create_re_raises_http_exception():
    class FakeRepository:
        def create_registro_uso_ia(self, **kwargs):
            _ = kwargs
            raise HTTPException(status_code=409, detail="conflito")

    service = UsoIARequestService(session="db")
    service._registro_repo = FakeRepository()

    with pytest.raises(HTTPException) as exc_info:
        service.create_uso_ia(current_user=SimpleNamespace(id=1), uso_ia_data=_uso_payload())

    assert exc_info.value.status_code == 409


def test_uso_ia_create_converts_generic_error_to_500():
    class FakeRepository:
        def create_registro_uso_ia(self, **kwargs):
            _ = kwargs
            raise RuntimeError("db down")

    service = UsoIARequestService(session="db")
    service._registro_repo = FakeRepository()

    with pytest.raises(HTTPException) as exc_info:
        service.create_uso_ia(current_user=SimpleNamespace(id=1), uso_ia_data=_uso_payload())

    assert exc_info.value.status_code == 500


def test_uso_ia_list_usuario_success_and_invalid_enum():
    class FakeRepository:
        def get_registros_uso_ia(self, **kwargs):
            self.last_kwargs = kwargs
            return [_uso_response_item()]

        def count_registros_uso_ia(self, **kwargs):
            self.count_kwargs = kwargs
            return 12

    repo = FakeRepository()
    service = UsoIARequestService(session="db")
    service._registro_repo = repo
    user = SimpleNamespace(id=7)

    page = service.list_usos_ia_usuario(
        current_user=user,
        skip=10,
        limit=5,
        tipo_geracao=models.TipoAcaoEnum.CRIACAO_PRODUTO.value,
        data_inicio=None,
        data_fim=None,
    )

    assert page.total_items == 12
    assert page.page == 3
    assert repo.last_kwargs["tipo_acao"] == models.TipoAcaoEnum.CRIACAO_PRODUTO

    with pytest.raises(HTTPException) as exc_info:
        service.list_usos_ia_usuario(
            current_user=user,
            skip=0,
            limit=10,
            tipo_geracao="nao-existe",
            data_inicio=None,
            data_fim=None,
        )

    assert exc_info.value.status_code == 422


def test_uso_ia_read_especifico_and_por_produto_paths():
    class FakeRegistroRepo:
        def __init__(self, registro):
            self.registro = registro
            self.calls = []

        def get_registro_uso_ia(self, *, registro_id):
            self.calls.append(("get_registro_uso_ia", registro_id))
            return self.registro

        def get_usos_ia_by_produto(self, **kwargs):
            self.calls.append(("get_usos_ia_by_produto", kwargs))
            return [SimpleNamespace(id=91)]

    class FakeProductRepo:
        def __init__(self, produto):
            self.produto = produto

        def get_produto(self, *, produto_id):
            _ = produto_id
            return self.produto

    user = SimpleNamespace(id=7, is_superuser=False)
    registro_repo = FakeRegistroRepo(SimpleNamespace(id=11, user_id=7))
    service = UsoIARequestService(session="db")
    service._registro_repo = registro_repo
    service._product_repo = FakeProductRepo(SimpleNamespace(id=20, user_id=7))

    assert service.read_uso_ia_especifico(current_user=user, registro_id=11).id == 11
    assert service.read_usos_ia_por_produto(current_user=user, produto_id=20, skip=0, limit=10)[0].id == 91
    assert registro_repo.calls[-1][1]["user_id"] == 7

    service._registro_repo = FakeRegistroRepo(None)
    with pytest.raises(HTTPException) as exc_info:
        service.read_uso_ia_especifico(current_user=user, registro_id=99)
    assert exc_info.value.status_code == 404

    service._registro_repo = FakeRegistroRepo(SimpleNamespace(id=11, user_id=88))
    with pytest.raises(HTTPException) as exc_info:
        service.read_uso_ia_especifico(current_user=user, registro_id=11)
    assert exc_info.value.status_code == 403

    service._product_repo = FakeProductRepo(None)
    with pytest.raises(HTTPException) as exc_info:
        service.read_usos_ia_por_produto(current_user=user, produto_id=20, skip=0, limit=10)
    assert exc_info.value.status_code == 404

    service._product_repo = FakeProductRepo(SimpleNamespace(id=20, user_id=88))
    with pytest.raises(HTTPException) as exc_info:
        service.read_usos_ia_por_produto(current_user=user, produto_id=20, skip=0, limit=10)
    assert exc_info.value.status_code == 403

    admin_user = SimpleNamespace(id=1, is_superuser=True)
    admin_repo = FakeRegistroRepo(SimpleNamespace(id=11, user_id=88))
    service._registro_repo = admin_repo
    service._product_repo = FakeProductRepo(SimpleNamespace(id=20, user_id=88))
    service.read_usos_ia_por_produto(current_user=admin_user, produto_id=20, skip=0, limit=10)
    assert admin_repo.calls[-1][1]["user_id"] == 88


def test_uso_ia_route_wrappers_delegate():
    user = SimpleNamespace(id=7)
    expected_page = schemas.UsoIAPage(items=[], total_items=0, page=1, limit=10)
    expected_record = SimpleNamespace(id=11)

    class FakeRequestService:
        def create_uso_ia(self, **kwargs):
            self.last = ("create", kwargs)
            return expected_record

        def list_usos_ia_usuario(self, **kwargs):
            self.last = ("list", kwargs)
            return expected_page

        def read_usos_ia_por_produto(self, **kwargs):
            self.last = ("produto", kwargs)
            return [expected_record]

        def read_uso_ia_especifico(self, **kwargs):
            self.last = ("registro", kwargs)
            return expected_record

    service = FakeRequestService()
    payload = _uso_payload()

    assert (
        uso_ia_router.create_uso_ia_endpoint(
            uso_ia_data=payload,
            current_user=user,
            request_service=service,
        )
        is expected_record
    )
    assert service.last[0] == "create"
    assert (
        uso_ia_router.read_usos_ia_usuario_logado(
            current_user=user,
            request_service=service,
            skip=0,
            limit=10,
            tipo_geracao=None,
            data_inicio=None,
            data_fim=None,
        )
        == expected_page
    )
    assert service.last[0] == "list"
    assert (
        uso_ia_router.read_usos_ia_por_produto(
            produto_id=20,
            current_user=user,
            request_service=service,
            skip=0,
            limit=10,
        )[0]
        is expected_record
    )
    assert service.last[0] == "produto"
    assert (
        uso_ia_router.read_uso_ia_especifico(
            registro_id=11,
            current_user=user,
            request_service=service,
        )
        is expected_record
    )
    assert service.last[0] == "registro"


@pytest.mark.asyncio
async def test_admin_analytics_counts_and_dependencies():
    class FakeAnalyticsRepo:
        def count_total_users(self):
            return 10

        def count_total_products(self):
            return 20

        def count_total_suppliers(self):
            return 30

        def count_ia_usage_since(self, *, start_at):
            self.start_at = start_at
            return 40

        def count_web_enrichment_usage_since(self, *, start_at):
            self.start_at = start_at
            return 50

    service = AdminAnalyticsRequestService(session="db")
    service._analytics_repository = FakeAnalyticsRepo()
    service._now_utc = lambda: datetime(2026, 3, 8, 12, tzinfo=timezone.utc)

    result = service.get_total_counts()

    assert result.total_usuarios == 10
    assert result.total_enriquecimentos_mes == 50
    assert service._analytics_repository.start_at.day == 1

    with pytest.raises(HTTPException) as exc_info:
        await admin_router._AdminAnalyticsDependencies.get_current_active_admin_user(
            current_user=SimpleNamespace(is_superuser=False)
        )
    assert exc_info.value.status_code == 403
    admin_user = await admin_router._AdminAnalyticsDependencies.get_current_active_admin_user(
        current_user=SimpleNamespace(is_superuser=True)
    )
    assert admin_user.is_superuser is True


def test_admin_analytics_total_counts_converts_error_to_500():
    class FakeAnalyticsRepo:
        def count_total_users(self):
            raise RuntimeError("db down")

    service = AdminAnalyticsRequestService(session="db")
    service._analytics_repository = FakeAnalyticsRepo()

    with pytest.raises(HTTPException) as exc_info:
        service.get_total_counts()

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_admin_analytics_lists_and_route_wrappers():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)

    class FakeUserRepo:
        def get_planos(self, **kwargs):
            _ = kwargs
            return [SimpleNamespace(id=1, nome="Pro")]

        def get_users(self, **kwargs):
            _ = kwargs
            return [SimpleNamespace(id=9, email="u@test.com", nome_completo="User", created_at=now)]

    class FakeHistoricoRepo:
        def get_registros_historico(self, *, skip, limit):
            return [SimpleNamespace(id=1, skip=skip, limit=limit)]

    class _StatusRow:
        def __init__(self, status_value, total):
            self._status_value = status_value
            self.total = total

        def __getitem__(self, index):
            assert index == 0
            return self._status_value

    class FakeAnalyticsRepo:
        def count_plan_usage_since(self, *, plano_id, start_at):
            _ = start_at
            return 7 if plano_id == 1 else 0

        def list_usage_by_action_since(self, *, start_at):
            _ = start_at
            return [SimpleNamespace(tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO.value, total_no_mes=5)]

        def count_products_by_user(self, *, user_id):
            return 3 if user_id == 9 else 0

        def count_ia_usage_by_user_since(self, *, user_id, start_at):
            _ = start_at
            return 2 if user_id == 9 else 0

        def list_product_status_counts(self):
            return [_StatusRow("CONCLUIDO", 8)]

        def list_recent_usage_records(self, *, limit):
            _ = limit
            return [SimpleNamespace(id=71, user_id=9, tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO, created_at=now)]

        def get_user_by_id(self, *, user_id):
            return SimpleNamespace(email=f"user{user_id}@test.com")

    service = AdminAnalyticsRequestService(session="db")
    service._user_repository = FakeUserRepo()
    service._historico_repository = FakeHistoricoRepo()
    service._analytics_repository = FakeAnalyticsRepo()
    service._now_utc = lambda: now

    assert service.get_uso_ia_por_plano()[0].total_geracoes_ia_no_mes == 7
    assert service.get_uso_ia_por_tipo()[0].total_no_mes == 5
    assert service.get_user_activity(skip=0, limit=10)[0].total_produtos == 3

    product_status_counts = service.get_product_status_counts()
    assert product_status_counts[0].status == "CONCLUIDO"
    assert product_status_counts[0].total == 8
    assert service.get_recent_activities(limit=10)[0].user_email == "user9@test.com"
    assert service.get_recent_historico(limit=10)[0].id == 1

    class FakeRequestService:
        def get_total_counts(self):
            return schemas.TotalCounts(
                total_usuarios=1,
                total_produtos=2,
                total_fornecedores=3,
                total_geracoes_ia_mes=4,
                total_enriquecimentos_mes=5,
            )

        def get_uso_ia_por_plano(self):
            return [schemas.UsoIAPorPlano(plano_id=1, nome_plano="Pro", total_geracoes_ia_no_mes=7)]

        def get_uso_ia_por_tipo(self):
            return [schemas.UsoIAPorTipo(tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO.value, total_no_mes=5)]

        def get_user_activity(self, **kwargs):
            self.last = kwargs
            return [schemas.UserActivity(user_id=1, email="u@test.com", nome_completo="User", created_at=now, total_produtos=1, total_geracoes_ia_mes_corrente=2)]

        def get_product_status_counts(self):
            return [schemas.ProductStatusCount(status=models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO, total=8)]

        def get_recent_activities(self, **kwargs):
            self.last = kwargs
            return [schemas.RecentActivity(id=1, user_id=1, user_email="u@test.com", tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO, created_at=now)]

        def get_recent_historico(self, **kwargs):
            self.last = kwargs
            return [SimpleNamespace(id=1)]

    request_service = FakeRequestService()
    assert (
        await admin_router.get_total_counts_endpoint(request_service=request_service)
    ).total_usuarios == 1
    assert (
        await admin_router.get_uso_ia_por_plano_endpoint(request_service=request_service)
    )[0].nome_plano == "Pro"
    assert (
        await admin_router.get_uso_ia_por_tipo_endpoint(request_service=request_service)
    )[0].total_no_mes == 5
    assert (
        await admin_router.get_user_activity_endpoint(
            skip=0,
            limit=10,
            request_service=request_service,
        )
    )[0].total_geracoes_ia_mes_corrente == 2
    assert (
        await admin_router.get_product_status_counts(request_service=request_service)
    )[0].status == models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
    assert (
        await admin_router.get_recent_activities(limit=10, request_service=request_service)
    )[0].user_email == "u@test.com"
    assert (
        await admin_router.get_recent_historico(limit=10, request_service=request_service)
    )[0].id == 1
