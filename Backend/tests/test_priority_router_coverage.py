"""Targeted coverage for priority routers in the backend roadmap."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import models, schemas
from Backend.auth import OAuthError
from Backend.routers import generation as generation_router
from Backend.routers import product_types as product_types_router
from Backend.routers import social_auth as social_auth_router
from Backend.routers.generation import GenerationRequestService
from Backend.routers.product_types import ProductTypesRequestService, ReorderRequest
from Backend.routers.social_auth import SocialAuthRequestService


def _product_type_create() -> schemas.ProductTypeCreate:
    return schemas.ProductTypeCreate(key_name="pesados", friendly_name="Pesados")


def _attribute_create(
    *,
    attribute_key: str = "material",
    label: str = "Material",
) -> schemas.AttributeTemplateCreate:
    return schemas.AttributeTemplateCreate(
        attribute_key=attribute_key,
        label=label,
        field_type=models.AttributeFieldTypeEnum.TEXT,
    )


def _attribute_update(**kwargs) -> schemas.AttributeTemplateUpdate:
    return schemas.AttributeTemplateUpdate(**kwargs)


def _suggestions_payload(produto_id: int = 11) -> schemas.SugestoesAtributosResponse:
    return schemas.SugestoesAtributosResponse(
        produto_id=produto_id,
        modelo_ia_utilizado="gemini-test",
        sugestoes_atributos=[
            schemas.SugestaoAtributoItem(chave_atributo="material", valor_sugerido="aco")
        ],
    )


class _FakeProductTypeRepo:
    def __init__(self):
        self.calls = []
        self.by_id = {}
        self.by_key = {}
        self.attribute_by_id = {}
        self.attribute_by_key = {}
        self.reorder_result = None
        self.created = None
        self.deleted = None
        self.updated = None
        self.updated_attribute = None

    def get_product_type_by_key_name(self, *, key_name, user_id=None):
        self.calls.append(("get_product_type_by_key_name", key_name, user_id))
        return self.by_key.get((key_name, user_id))

    def create_product_type(self, *, product_type_create, user_id=None):
        self.calls.append(("create_product_type", product_type_create.key_name, user_id))
        self.created = SimpleNamespace(
            id=91,
            user_id=user_id,
            key_name=product_type_create.key_name,
            friendly_name=product_type_create.friendly_name,
        )
        return self.created

    def get_product_type(self, *, product_type_id):
        self.calls.append(("get_product_type", product_type_id))
        return self.by_id.get(product_type_id)

    def get_product_types_for_user(self, *, skip, limit, user_id):
        self.calls.append(("get_product_types_for_user", skip, limit, user_id))
        return [SimpleNamespace(id=1, key_name="auto", user_id=user_id)]

    def update_product_type(self, *, db_product_type, product_type_update):
        self.calls.append(("update_product_type", db_product_type.id))
        self.updated = SimpleNamespace(
            id=db_product_type.id,
            user_id=db_product_type.user_id,
            **product_type_update.model_dump(exclude_unset=True),
        )
        return self.updated

    def delete_product_type(self, *, db_product_type):
        self.calls.append(("delete_product_type", db_product_type.id))
        self.deleted = db_product_type
        return db_product_type

    def get_attribute_template(self, *, attribute_template_id):
        self.calls.append(("get_attribute_template", attribute_template_id))
        return self.attribute_by_id.get(attribute_template_id)

    def get_attribute_template_by_key(self, *, product_type_id, attribute_key, exclude_attribute_id=None):
        self.calls.append(
            ("get_attribute_template_by_key", product_type_id, attribute_key, exclude_attribute_id)
        )
        return self.attribute_by_key.get((product_type_id, attribute_key, exclude_attribute_id))

    def create_attribute_template(self, *, attr_template_create, product_type_id):
        self.calls.append(("create_attribute_template", product_type_id, attr_template_create.attribute_key))
        return SimpleNamespace(id=701, product_type_id=product_type_id, **attr_template_create.model_dump())

    def update_attribute_template(self, *, db_attr_template, attr_template_update):
        _ = attr_template_update
        self.calls.append(("update_attribute_template", db_attr_template.id))
        return self.updated_attribute

    def delete_attribute_template(self, *, db_attr_template):
        self.calls.append(("delete_attribute_template", db_attr_template.id))
        return self.deleted

    def reorder_attribute_template(self, *, attribute_id, direction):
        self.calls.append(("reorder_attribute_template", attribute_id, direction))
        return self.reorder_result


class _FakeHistoricoRepo:
    def __init__(self):
        self.entries = []

    def create_registro_historico(self, *, registro_in):
        self.entries.append(registro_in)
        return registro_in


def _build_product_types_service() -> ProductTypesRequestService:
    service = ProductTypesRequestService(session="db")
    service._product_type_repo = _FakeProductTypeRepo()
    service._historico_repo = _FakeHistoricoRepo()
    return service


def test_generation_helpers_delegate_to_scheduling_service():
    called = []

    class FakeSchedulingService:
        def validate_product_access(self, **kwargs):
            called.append(("validate_product_access", kwargs))
            return {"produto": kwargs["produto_id"]}

        def mark_pending_status(self, **kwargs):
            called.append(("mark_pending_status", kwargs))

    service = GenerationRequestService(session="db")
    service._generation_scheduling_service = FakeSchedulingService()
    user = SimpleNamespace(id=4)

    result = service._validate_product_access(produto_id=21, current_user=user)
    service._mark_pending_status(db_produto="produto", generation_type="titulo")

    assert result == {"produto": 21}
    assert called[0] == ("validate_product_access", {"produto_id": 21, "current_user": user})
    assert called[1] == (
        "mark_pending_status",
        {"db_produto": "produto", "generation_type": "titulo"},
    )


@pytest.mark.parametrize(
    ("method_name", "payload", "expected_generation_type", "expected_extra"),
    [
        (
            "agendar_geracao_nova_descricao_openai",
            {"produto_id": 31, "background_tasks": SimpleNamespace(), "tamanho_palavras": 120},
            "descricao",
            ("tamanho_palavras", 120),
        ),
        (
            "agendar_geracao_novos_titulos_basico",
            {
                "produto_id": 32,
                "background_tasks": SimpleNamespace(),
                "num_titulos": 5,
                "template_titulo": "tmpl",
            },
            "titulo",
            ("template_titulo", "tmpl"),
        ),
        (
            "agendar_geracao_novos_titulos_gemini",
            {"produto_id": 33, "background_tasks": SimpleNamespace(), "num_titulos": 4},
            "titulo",
            ("num_titulos", 4),
        ),
        (
            "agendar_geracao_nova_descricao_gemini",
            {"produto_id": 34, "background_tasks": SimpleNamespace(), "tamanho_palavras": 160},
            "descricao",
            ("tamanho_palavras", 160),
        ),
    ],
)
def test_generation_request_methods_cover_success_paths(
    method_name,
    payload,
    expected_generation_type,
    expected_extra,
):
    called = []

    class FakeSchedulingService:
        def enqueue_generation_task(self, **kwargs):
            called.append(("enqueue_generation_task", kwargs))

    service = GenerationRequestService(session="db")
    service._generation_scheduling_service = FakeSchedulingService()
    service._validate_product_access = lambda **kwargs: called.append(
        ("validate_product_access", kwargs)
    ) or SimpleNamespace(id=kwargs["produto_id"])
    service._mark_pending_status = lambda **kwargs: called.append(("mark_pending_status", kwargs))
    service._ia_generation_service = SimpleNamespace(
        gerar_descricao_com_openai="fn_openai_desc",
        gerar_titulos_com_gemini="fn_gemini_titulos",
        gerar_descricao_com_gemini="fn_gemini_desc",
    )
    service._basic_generation_service = SimpleNamespace(gerar_titulos_basicos="fn_basic_titles")
    user = SimpleNamespace(id=8)

    result = getattr(service, method_name)(current_user=user, **payload)

    assert str(payload["produto_id"]) in result["msg"]
    assert called[0][0] == "validate_product_access"
    if "basico" in method_name or "gemini" in method_name:
        assert called[1][0] == "mark_pending_status"
        enqueue_call = called[2][1]
    else:
        enqueue_call = called[1][1]
    assert enqueue_call["produto_id"] == payload["produto_id"]
    assert enqueue_call["user_id"] == 8
    assert enqueue_call["generation_type"] == expected_generation_type
    assert enqueue_call[expected_extra[0]] == expected_extra[1]


@pytest.mark.asyncio
async def test_generation_sugestao_repassa_http_exception():
    class FakeIAService:
        async def sugerir_valores_atributos_com_gemini(self, **_kwargs):
            raise HTTPException(status_code=422, detail="erro de dominio")

    service = GenerationRequestService(session="db")
    service._ia_generation_service = FakeIAService()

    with pytest.raises(HTTPException) as exc_info:
        await service.sugerir_atributos_para_produto_com_gemini(
            produto_id=99,
            current_user=SimpleNamespace(id=5),
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_generation_sugestao_converte_erro_generico_em_500():
    class FakeIAService:
        async def sugerir_valores_atributos_com_gemini(self, **_kwargs):
            raise RuntimeError("boom")

    service = GenerationRequestService(session="db")
    service._ia_generation_service = FakeIAService()

    with pytest.raises(HTTPException) as exc_info:
        await service.sugerir_atributos_para_produto_com_gemini(
            produto_id=99,
            current_user=SimpleNamespace(id=5),
        )

    assert exc_info.value.status_code == 500
    assert "erro interno" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route_fn", "kwargs", "expected_call", "expected_result"),
    [
        (
            generation_router.agendar_geracao_novos_titulos_openai,
            {"produto_id": 1, "background_tasks": SimpleNamespace(), "num_titulos": 3},
            ("agendar_geracao_novos_titulos_openai", {"produto_id": 1, "num_titulos": 3}),
            {"msg": "openai-titulos"},
        ),
        (
            generation_router.agendar_geracao_nova_descricao_openai,
            {"produto_id": 2, "background_tasks": SimpleNamespace(), "tamanho_palavras": 120},
            ("agendar_geracao_nova_descricao_openai", {"produto_id": 2, "tamanho_palavras": 120}),
            {"msg": "openai-descricao"},
        ),
        (
            generation_router.agendar_geracao_novos_titulos_basico,
            {
                "produto_id": 3,
                "background_tasks": SimpleNamespace(),
                "num_titulos": 5,
                "template": "tmpl",
            },
            ("agendar_geracao_novos_titulos_basico", {"produto_id": 3, "num_titulos": 5, "template_titulo": "tmpl"}),
            {"msg": "basic-titulos"},
        ),
        (
            generation_router.agendar_geracao_nova_descricao_basica,
            {
                "produto_id": 4,
                "background_tasks": SimpleNamespace(),
                "tamanho_palavras": 180,
                "template": "tmpl-desc",
            },
            (
                "agendar_geracao_nova_descricao_basica",
                {"produto_id": 4, "tamanho_palavras": 180, "template_descricao": "tmpl-desc"},
            ),
            {"msg": "basic-descricao"},
        ),
        (
            generation_router.agendar_geracao_novos_titulos_gemini,
            {"produto_id": 5, "background_tasks": SimpleNamespace(), "num_titulos": 6},
            ("agendar_geracao_novos_titulos_gemini", {"produto_id": 5, "num_titulos": 6}),
            {"msg": "gemini-titulos"},
        ),
        (
            generation_router.agendar_geracao_nova_descricao_gemini,
            {"produto_id": 6, "background_tasks": SimpleNamespace(), "tamanho_palavras": 150},
            ("agendar_geracao_nova_descricao_gemini", {"produto_id": 6, "tamanho_palavras": 150}),
            {"msg": "gemini-descricao"},
        ),
    ],
)
async def test_generation_route_wrappers_delegate_to_request_service(
    route_fn,
    kwargs,
    expected_call,
    expected_result,
):
    user = SimpleNamespace(id=77)
    called = []

    class FakeRequestService:
        def agendar_geracao_novos_titulos_openai(self, **inner_kwargs):
            called.append(("agendar_geracao_novos_titulos_openai", inner_kwargs))
            return {"msg": "openai-titulos"}

        def agendar_geracao_nova_descricao_openai(self, **inner_kwargs):
            called.append(("agendar_geracao_nova_descricao_openai", inner_kwargs))
            return {"msg": "openai-descricao"}

        def agendar_geracao_novos_titulos_basico(self, **inner_kwargs):
            called.append(("agendar_geracao_novos_titulos_basico", inner_kwargs))
            return {"msg": "basic-titulos"}

        def agendar_geracao_nova_descricao_basica(self, **inner_kwargs):
            called.append(("agendar_geracao_nova_descricao_basica", inner_kwargs))
            return {"msg": "basic-descricao"}

        def agendar_geracao_novos_titulos_gemini(self, **inner_kwargs):
            called.append(("agendar_geracao_novos_titulos_gemini", inner_kwargs))
            return {"msg": "gemini-titulos"}

        def agendar_geracao_nova_descricao_gemini(self, **inner_kwargs):
            called.append(("agendar_geracao_nova_descricao_gemini", inner_kwargs))
            return {"msg": "gemini-descricao"}

    result = await route_fn(
        request_service=FakeRequestService(),
        current_user=user,
        **kwargs,
    )

    assert result == expected_result
    assert called[0][0] == expected_call[0]
    for key, value in expected_call[1].items():
        assert called[0][1][key] == value
    assert called[0][1]["current_user"] is user


@pytest.mark.asyncio
async def test_generation_route_wrapper_for_sugerir_atributos_delegate():
    called = []
    expected = _suggestions_payload(produto_id=7)
    user = SimpleNamespace(id=88)

    class FakeRequestService:
        async def sugerir_atributos_para_produto_com_gemini(self, **kwargs):
            called.append(kwargs)
            return expected

    result = await generation_router.sugerir_atributos_para_produto_com_gemini(
        produto_id=7,
        request_service=FakeRequestService(),
        current_user=user,
    )

    assert result == expected
    assert called == [{"produto_id": 7, "current_user": user}]


def test_product_types_create_success_for_regular_user_records_history():
    service = _build_product_types_service()
    user = SimpleNamespace(id=7, is_superuser=False)

    result = service.create_product_type(product_type_in=_product_type_create(), current_user=user)

    assert result.id == 91
    assert service._product_type_repo.created.user_id == 7
    assert service._historico_repo.entries[0].entity_id == 91
    assert service._historico_repo.entries[0].acao == models.TipoAcaoSistemaEnum.CRIACAO


def test_product_types_create_superuser_checks_global_scope_before_creating():
    service = _build_product_types_service()
    user = SimpleNamespace(id=1, is_superuser=True)

    result = service.create_product_type(product_type_in=_product_type_create(), current_user=user)

    assert result.user_id is None
    assert service._product_type_repo.calls[:2] == [
        ("get_product_type_by_key_name", "pesados", None),
        ("get_product_type_by_key_name", "pesados", None),
    ]


@pytest.mark.asyncio
async def test_product_types_read_details_by_numeric_id_success():
    service = _build_product_types_service()
    owned = SimpleNamespace(id=55, key_name="pesados", user_id=7)
    service._product_type_repo.by_id[55] = owned

    result = await service.read_product_type_details(
        identifier="55",
        current_user=SimpleNamespace(id=7, is_superuser=False),
    )

    assert result is owned


@pytest.mark.asyncio
async def test_product_types_read_details_not_found_raises_404():
    service = _build_product_types_service()

    with pytest.raises(HTTPException) as exc_info:
        await service.read_product_type_details(
            identifier="nao-existe",
            current_user=SimpleNamespace(id=7, is_superuser=False),
        )

    assert exc_info.value.status_code == 404


def test_product_types_update_success_records_history():
    service = _build_product_types_service()
    service._product_type_repo.by_id[55] = SimpleNamespace(id=55, user_id=7)

    result = service.update_product_type(
        type_id=55,
        product_type_in=schemas.ProductTypeUpdate(friendly_name="Atualizado"),
        current_user=SimpleNamespace(id=7, is_superuser=False),
    )

    assert result.friendly_name == "Atualizado"
    assert service._historico_repo.entries[0].acao == models.TipoAcaoSistemaEnum.ATUALIZACAO


def test_product_types_update_not_found_raises_404():
    service = _build_product_types_service()

    with pytest.raises(HTTPException) as exc_info:
        service.update_product_type(
            type_id=77,
            product_type_in=schemas.ProductTypeUpdate(friendly_name="Atualizado"),
            current_user=SimpleNamespace(id=7, is_superuser=False),
        )

    assert exc_info.value.status_code == 404


def test_product_types_delete_success_records_history():
    service = _build_product_types_service()
    service._product_type_repo.by_id[55] = SimpleNamespace(id=55, user_id=7)

    result = service.delete_product_type(
        type_id=55,
        current_user=SimpleNamespace(id=7, is_superuser=False),
    )

    assert result.id == 55
    assert service._historico_repo.entries[0].acao == models.TipoAcaoSistemaEnum.DELECAO


def test_product_types_delete_not_found_raises_404():
    service = _build_product_types_service()

    with pytest.raises(HTTPException) as exc_info:
        service.delete_product_type(type_id=55, current_user=SimpleNamespace(id=7, is_superuser=False))

    assert exc_info.value.status_code == 404


def test_product_types_add_attribute_success():
    service = _build_product_types_service()

    result = service.add_attribute_to_product_type(type_id=91, attribute_in=_attribute_create())

    assert result.product_type_id == 91
    assert result.attribute_key == "material"


def test_product_types_update_attribute_duplicate_new_key_rejects():
    service = _build_product_types_service()
    service._product_type_repo.attribute_by_id[11] = SimpleNamespace(
        id=11,
        product_type_id=91,
        attribute_key="cor",
    )
    service._product_type_repo.attribute_by_key[(91, "material", 11)] = SimpleNamespace(id=99)

    with pytest.raises(HTTPException) as exc_info:
        service.update_attribute_for_product_type(
            type_id=91,
            attribute_id=11,
            attribute_in=_attribute_update(attribute_key="material"),
        )

    assert exc_info.value.status_code == 400


def test_product_types_update_attribute_repository_failure_becomes_404():
    service = _build_product_types_service()
    service._product_type_repo.attribute_by_id[11] = SimpleNamespace(
        id=11,
        product_type_id=91,
        attribute_key="cor",
    )
    service._product_type_repo.updated_attribute = None

    with pytest.raises(HTTPException) as exc_info:
        service.update_attribute_for_product_type(
            type_id=91,
            attribute_id=11,
            attribute_in=_attribute_update(label="Cor Principal"),
        )

    assert exc_info.value.status_code == 404


def test_product_types_update_attribute_success():
    service = _build_product_types_service()
    service._product_type_repo.attribute_by_id[11] = SimpleNamespace(
        id=11,
        product_type_id=91,
        attribute_key="cor",
    )
    service._product_type_repo.updated_attribute = SimpleNamespace(
        id=11,
        product_type_id=91,
        label="Cor Principal",
    )

    result = service.update_attribute_for_product_type(
        type_id=91,
        attribute_id=11,
        attribute_in=_attribute_update(label="Cor Principal"),
    )

    assert result.label == "Cor Principal"


def test_product_types_remove_attribute_repository_failure_becomes_404():
    service = _build_product_types_service()
    service._product_type_repo.attribute_by_id[11] = SimpleNamespace(id=11, product_type_id=91)
    service._product_type_repo.deleted = None

    with pytest.raises(HTTPException) as exc_info:
        service.remove_attribute_from_product_type(type_id=91, attribute_id=11)

    assert exc_info.value.status_code == 404


def test_product_types_remove_attribute_success():
    service = _build_product_types_service()
    service._product_type_repo.attribute_by_id[11] = SimpleNamespace(id=11, product_type_id=91)
    service._product_type_repo.deleted = SimpleNamespace(id=11, product_type_id=91)

    result = service.remove_attribute_from_product_type(type_id=91, attribute_id=11)

    assert result.id == 11


def test_product_types_reorder_missing_type_raises_404():
    service = _build_product_types_service()

    with pytest.raises(HTTPException) as exc_info:
        service.reorder_attribute(
            type_id=91,
            attribute_id=11,
            reorder_request=ReorderRequest(direction="up"),
            current_user=SimpleNamespace(id=7, is_superuser=False),
        )

    assert exc_info.value.status_code == 404


def test_product_types_reorder_success_returns_reordered_attribute():
    service = _build_product_types_service()
    service._product_type_repo.by_id[91] = SimpleNamespace(id=91, user_id=7)
    service._product_type_repo.reorder_result = SimpleNamespace(id=11, product_type_id=91)

    result = service.reorder_attribute(
        type_id=91,
        attribute_id=11,
        reorder_request=ReorderRequest(direction="down"),
        current_user=SimpleNamespace(id=7, is_superuser=False),
    )

    assert result.id == 11


@pytest.mark.asyncio
async def test_product_types_route_read_details_delegates():
    called = []
    user = SimpleNamespace(id=7)
    expected = SimpleNamespace(id=55)

    class FakeRequestService:
        async def read_product_type_details(self, **kwargs):
            called.append(kwargs)
            return expected

    result = await product_types_router.read_product_type_details_route(
        type_id_or_key_path="55",
        current_user=user,
        request_service=FakeRequestService(),
    )

    assert result is expected
    assert called == [{"identifier": "55", "current_user": user}]


@pytest.mark.parametrize(
    ("route_fn", "kwargs", "expected_result"),
    [
        (
            product_types_router.create_product_type_endpoint,
            {"product_type_in": _product_type_create()},
            SimpleNamespace(id=1),
        ),
        (
            product_types_router.read_product_types_endpoint,
            {"skip": 5, "limit": 20},
            [SimpleNamespace(id=1)],
        ),
        (
            product_types_router.update_product_type_endpoint,
            {"type_id": 9, "product_type_in": schemas.ProductTypeUpdate(friendly_name="Novo")},
            SimpleNamespace(id=9),
        ),
        (
            product_types_router.delete_product_type_endpoint,
            {"type_id": 9},
            SimpleNamespace(id=9),
        ),
        (
            product_types_router.add_attribute_to_product_type_endpoint,
            {"type_id": 9, "attribute_in": _attribute_create()},
            SimpleNamespace(id=11),
        ),
        (
            product_types_router.update_attribute_for_product_type_endpoint,
            {"type_id": 9, "attribute_id": 11, "attribute_in": _attribute_update(label="Novo")},
            SimpleNamespace(id=11),
        ),
        (
            product_types_router.remove_attribute_from_product_type_endpoint,
            {"type_id": 9, "attribute_id": 11},
            SimpleNamespace(id=11),
        ),
        (
            product_types_router.reorder_attribute_endpoint,
            {"type_id": 9, "attribute_id": 11, "reorder_request": ReorderRequest(direction="up")},
            SimpleNamespace(id=11),
        ),
    ],
)
def test_product_types_route_wrappers_delegate(route_fn, kwargs, expected_result):
    user = SimpleNamespace(id=7)

    class FakeRequestService:
        def create_product_type(self, **_kwargs):
            return expected_result

        def read_product_types(self, **_kwargs):
            return expected_result

        def update_product_type(self, **_kwargs):
            return expected_result

        def delete_product_type(self, **_kwargs):
            return expected_result

        def add_attribute_to_product_type(self, **_kwargs):
            return expected_result

        def update_attribute_for_product_type(self, **_kwargs):
            return expected_result

        def remove_attribute_from_product_type(self, **_kwargs):
            return expected_result

        def reorder_attribute(self, **_kwargs):
            return expected_result

    result = route_fn(current_user=user, request_service=FakeRequestService(), **kwargs)
    assert result is expected_result


def test_social_auth_static_has_client_and_default_resolution(monkeypatch):
    monkeypatch.setattr(social_auth_router.oauth, "_clients", {"google": object()})
    monkeypatch.setattr(social_auth_router.settings, "PRODUCT_EXPERIENCE_DEFAULT", "  invalid  ", raising=False)

    assert SocialAuthRequestService._has_client("google") is True
    assert SocialAuthRequestService._has_client("facebook") is False
    assert SocialAuthRequestService._resolve_product_experience_default() == "basic"


@pytest.mark.asyncio
async def test_social_auth_static_oauth_helpers_delegate(monkeypatch):
    class FakeResponse:
        def json(self):
            return {"email": "user@test.com"}

    class FakeClient:
        async def authorize_redirect(self, request, redirect_uri):
            return {"request": request, "redirect_uri": redirect_uri}

        async def authorize_access_token(self, request):
            return {"token": request}

        async def parse_id_token(self, request, token):
            return {"request": request, "token": token}

        async def get(self, path, token):
            assert path == "userinfo"
            return FakeResponse()

    fake_oauth = SimpleNamespace(
        _clients={"google": object(), "facebook": object()},
        google=FakeClient(),
        facebook=FakeClient(),
    )
    monkeypatch.setattr(social_auth_router, "oauth", fake_oauth)

    redirect = await SocialAuthRequestService._authorize_redirect("google", "req", "uri")
    token = await SocialAuthRequestService._authorize_access_token("facebook", "req-token")
    parsed = await SocialAuthRequestService._parse_google_id_token("req", {"access": "token"})
    userinfo = await SocialAuthRequestService._get_userinfo("facebook", {"access": "token"})

    assert redirect["redirect_uri"] == "uri"
    assert token == {"token": "req-token"}
    assert parsed["token"] == {"access": "token"}
    assert userinfo == {"email": "user@test.com"}


@pytest.mark.asyncio
async def test_social_auth_google_login_rejects_missing_client():
    service = SocialAuthRequestService(session="db")
    service._has_client = lambda provider: False

    with pytest.raises(HTTPException) as exc_info:
        await service.google_login(request=object())

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_social_auth_google_login_redirects_when_configured(monkeypatch):
    service = SocialAuthRequestService(session="db")
    service._has_client = lambda provider: True

    async def authorize_redirect(provider, request, redirect_uri):
        return {
            "provider": provider,
            "request": request,
            "redirect_uri": redirect_uri,
        }

    service._authorize_redirect = authorize_redirect
    monkeypatch.setattr(social_auth_router.settings, "GOOGLE_REDIRECT_URI", "http://google/callback", raising=False)

    result = await service.google_login(request="request")

    assert result["provider"] == "google"
    assert result["redirect_uri"] == "http://google/callback"


@pytest.mark.asyncio
async def test_social_auth_google_callback_unavailable_and_oauth_error():
    service = SocialAuthRequestService(session="db")
    service._has_client = lambda provider: False

    with pytest.raises(HTTPException) as exc_info:
        await service.google_callback(request=object())
    assert exc_info.value.status_code == 503

    service._has_client = lambda provider: True

    async def fail_authorize(_provider, _request):
        raise OAuthError("bad")

    service._authorize_access_token = fail_authorize

    with pytest.raises(HTTPException) as exc_info:
        await service.google_callback(request=object())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_social_auth_google_callback_fallback_and_missing_user():
    service = SocialAuthRequestService(session="db")
    service._has_client = lambda provider: True

    async def authorize_access_token(_provider, _request):
        return {"access": "token"}

    async def fail_parse(_request, _token):
        raise RuntimeError("parse failed")

    async def fallback_userinfo(_provider, _token):
        return {"sub": "fallback"}

    class FakeAuthWorkflow:
        async def process_google_login(self, google_userinfo):
            assert google_userinfo == {"sub": "fallback"}
            return None

        def create_access_token(self, payload):
            return payload

        def create_refresh_token(self, payload):
            return payload

    service._authorize_access_token = authorize_access_token
    service._parse_google_id_token = fail_parse
    service._get_userinfo = fallback_userinfo
    service._auth_workflow = FakeAuthWorkflow()

    with pytest.raises(HTTPException) as exc_info:
        await service.google_callback(request=object())

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_social_auth_facebook_login_and_callback_reject_missing_client():
    service = SocialAuthRequestService(session="db")
    service._has_client = lambda provider: False

    with pytest.raises(HTTPException) as exc_info:
        await service.facebook_login(request=object())
    assert exc_info.value.status_code == 503

    with pytest.raises(HTTPException) as exc_info:
        await service.facebook_callback(request=object())
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_social_auth_facebook_login_and_callback_paths(monkeypatch):
    service = SocialAuthRequestService(session="db")
    service._has_client = lambda provider: provider == "facebook"
    monkeypatch.setattr(
        social_auth_router.settings,
        "FACEBOOK_REDIRECT_URI",
        "http://facebook/callback",
        raising=False,
    )

    async def authorize_redirect(provider, request, redirect_uri):
        return {"provider": provider, "redirect_uri": redirect_uri, "request": request}

    service._authorize_redirect = authorize_redirect
    login_result = await service.facebook_login(request="req")
    assert login_result["provider"] == "facebook"

    async def fail_authorize(_provider, _request):
        raise OAuthError("bad")

    service._authorize_access_token = fail_authorize
    with pytest.raises(HTTPException) as exc_info:
        await service.facebook_callback(request=object())
    assert exc_info.value.status_code == 400

    async def success_authorize(_provider, _request):
        return {"access": "token"}

    async def get_userinfo(_provider, _token):
        return {"email": "fb@test.com"}

    class FakeAuthWorkflow:
        def __init__(self, user):
            self._user = user

        async def process_facebook_login(self, facebook_userinfo):
            assert facebook_userinfo == {"email": "fb@test.com"}
            return self._user

        def create_access_token(self, payload):
            return f"access:{payload['user_id']}"

        def create_refresh_token(self, payload):
            return f"refresh:{payload['user_id']}"

    service._authorize_access_token = success_authorize
    service._get_userinfo = get_userinfo
    service._auth_workflow = FakeAuthWorkflow(None)
    with pytest.raises(HTTPException) as exc_info:
        await service.facebook_callback(request=object())
    assert exc_info.value.status_code == 400

    service._auth_workflow = FakeAuthWorkflow(SimpleNamespace(id=18, email="fb@test.com"))
    token = await service.facebook_callback(request=object())
    assert token.access_token == "access:18"
    assert token.token_type == "bearer"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route_fn", "expected_result"),
    [
        (social_auth_router.social_login_config, schemas.SocialLoginConfig(google_enabled=True, facebook_enabled=False, product_experience_default="basic", allow_admin_experience_preview=True)),
        (social_auth_router.google_login, {"provider": "google"}),
        (social_auth_router.google_callback, schemas.Token(access_token="a", refresh_token="b", token_type="bearer")),
        (social_auth_router.facebook_login, {"provider": "facebook"}),
        (social_auth_router.facebook_callback, schemas.Token(access_token="c", refresh_token="d", token_type="bearer")),
    ],
)
async def test_social_auth_route_wrappers_delegate(route_fn, expected_result):
    class FakeRequestService:
        def social_login_config(self):
            return expected_result

        async def google_login(self, request):
            assert request == "request"
            return expected_result

        async def google_callback(self, request):
            assert request == "request"
            return expected_result

        async def facebook_login(self, request):
            assert request == "request"
            return expected_result

        async def facebook_callback(self, request):
            assert request == "request"
            return expected_result

    if route_fn is social_auth_router.social_login_config:
        result = await route_fn(request_service=FakeRequestService())
    else:
        result = await route_fn(request="request", request_service=FakeRequestService())

    assert result == expected_result
