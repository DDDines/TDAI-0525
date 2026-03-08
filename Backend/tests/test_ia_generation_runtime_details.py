"""Detailed coverage for IA generation runtime helpers and provider branches."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from Backend.testing.runtime_apis import ia_service


class _ResponseStub:
    def __init__(self, *, json_data=None, text="ok", status_error=None):
        self._json_data = json_data
        self.text = text
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._json_data


class _AsyncClientStub:
    def __init__(self, *, response=None, error=None, timeout=None):
        self.response = response
        self.error = error
        self.timeout = timeout
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.response

    async def post(self, *args, **kwargs):
        return await self.request("POST", *args, **kwargs)


class _SequenceAsyncClientStub(_AsyncClientStub):
    def __init__(self, *, responses=None, error=None, timeout=None):
        super().__init__(response=None, error=error, timeout=timeout)
        self._responses = list(responses or [])

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        if not self._responses:
            raise AssertionError("No stubbed responses left for request")
        return self._responses.pop(0)


class _UsageRepositoryStub:
    created: list = []

    def __init__(self, _db):
        pass

    def create_registro_uso_ia(self, registro_uso):
        self.created.append(registro_uso)
        return registro_uso


class _ProductRepositoryStub:
    produto = None

    def __init__(self, _db):
        pass

    def get_produto(self, produto_id):
        _ = produto_id
        return self.produto


class _ProviderWorkflowStub:
    def __init__(
        self,
        *,
        openai_key="sk-openai-valida",
        gemini_key="gemini-key",
        openai_result="1. Titulo A\n2. Titulo B",
        gemini_result="1. Titulo G\n2. Titulo H",
        suggestion_result=None,
        openai_results=None,
        gemini_results=None,
    ):
        self.openai_key = openai_key
        self.gemini_key = gemini_key
        self.openai_result = openai_result
        self.gemini_result = gemini_result
        self.openai_results = list(openai_results or [])
        self.gemini_results = list(gemini_results or [])
        self.suggestion_result = suggestion_result or {
            "sugestoes_atributos": [
                {"chave_atributo": "cor", "valor_sugerido": "Azul"},
                {"chave_atributo": "invalido", "valor_sugerido": "Ignorar"},
            ]
        }

    async def get_openai_api_key(self, db, user):
        _ = db, user
        return self.openai_key

    async def get_gemini_api_key(self, db, user):
        _ = db, user
        return self.gemini_key

    async def call_openai_api(self, **_kwargs):
        if self.openai_results:
            return self.openai_results.pop(0)
        return self.openai_result

    async def call_gemini_api(self, **_kwargs):
        if self.gemini_results:
            return self.gemini_results.pop(0)
        return self.gemini_result

    async def call_gemini_api_for_suggestions(self, **_kwargs):
        return self.suggestion_result


def _http_status_error(status_code: int, *, text: str, json_data=None):
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(status_code, request=request, text=text, json=json_data)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.asyncio
async def test_ai_provider_runtime_openai_http_paths(monkeypatch):
    runtime = ia_service.AiProviderRuntime()

    with pytest.raises(HTTPException) as missing_key:
        await runtime.call_openai_api(prompt_messages=[], api_key="")
    assert missing_key.value.status_code == 400

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=60.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                json_data={"choices": [{"message": {"content": "  titulo gerado  "}}]}
            ),
        ),
    )
    assert await runtime.call_openai_api(prompt_messages=[{"role": "user", "content": "hi"}], api_key="k") == "titulo gerado"

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=60.0: _AsyncClientStub(timeout=timeout, response=_ResponseStub(json_data={})),
    )
    with pytest.raises(HTTPException) as bad_structure:
        await runtime.call_openai_api(prompt_messages=[], api_key="k")
    assert bad_structure.value.status_code == 500

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=60.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(status_error=_http_status_error(429, text="rate limit")),
        ),
    )
    with pytest.raises(HTTPException) as upstream_error:
        await runtime.call_openai_api(prompt_messages=[], api_key="k")
    assert upstream_error.value.status_code == 429

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=60.0: _AsyncClientStub(timeout=timeout, error=RuntimeError("offline")),
    )
    with pytest.raises(HTTPException) as generic_error:
        await runtime.call_openai_api(prompt_messages=[], api_key="k")
    assert generic_error.value.status_code == 500


@pytest.mark.asyncio
async def test_ai_provider_runtime_routes_openai_compatible_calls_to_lm_studio(monkeypatch):
    runtime = ia_service.AiProviderRuntime()
    client_stub = _SequenceAsyncClientStub(
        responses=[
            _ResponseStub(json_data={"data": [{"id": "google/gemma-3-12b"}]}),
            _ResponseStub(
                json_data={"choices": [{"message": {"content": "titulo local"}}]}
            ),
        ]
    )
    monkeypatch.setattr(ia_service.settings, "AI_PROVIDER", "lm_studio", raising=False)
    monkeypatch.setattr(ia_service.settings, "LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1", raising=False)
    monkeypatch.setattr(ia_service.settings, "LM_STUDIO_MODEL", None, raising=False)
    monkeypatch.setattr(ia_service.settings, "LM_STUDIO_API_KEY", "lm-studio", raising=False)
    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=60.0: client_stub,
    )

    result = await runtime.call_openai_api(
        prompt_messages=[{"role": "user", "content": "hi"}],
        api_key="lm-studio",
    )

    assert result == "titulo local"
    assert runtime.get_openai_provider_name() == "lm_studio"
    assert client_stub.calls[0][1] == "http://127.0.0.1:1234/v1/models"
    assert client_stub.calls[1][1] == "http://127.0.0.1:1234/v1/chat/completions"
    assert client_stub.calls[1][2]["json"]["model"] == "google/gemma-3-12b"


@pytest.mark.asyncio
async def test_ai_provider_runtime_openai_request_error_returns_503(monkeypatch):
    runtime = ia_service.AiProviderRuntime()
    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=60.0: _AsyncClientStub(
            timeout=timeout,
            error=httpx.ConnectError("offline", request=httpx.Request("POST", "https://example.com")),
        ),
    )

    with pytest.raises(HTTPException) as upstream_error:
        await runtime.call_openai_api(prompt_messages=[], api_key="k")

    assert upstream_error.value.status_code == 503


@pytest.mark.asyncio
async def test_ai_provider_runtime_resolve_openai_model_branches(monkeypatch):
    runtime = ia_service.AiProviderRuntime()

    monkeypatch.setattr(ia_service.settings, "AI_PROVIDER", "lm_studio", raising=False)
    monkeypatch.setattr(ia_service.settings, "LM_STUDIO_MODEL", "google/gemma-3-12b", raising=False)
    assert await runtime.resolve_openai_model(api_key="lm-studio") == "google/gemma-3-12b"

    monkeypatch.setattr(ia_service.settings, "LM_STUDIO_MODEL", None, raising=False)
    runtime._lm_studio_model_cache = "cached/model"
    assert await runtime.resolve_openai_model(api_key="lm-studio") == "cached/model"

    assert (
        await runtime.resolve_openai_model(
            api_key="lm-studio",
            requested_model="custom/local-model",
        )
        == "custom/local-model"
    )

    client_stub = _SequenceAsyncClientStub(responses=[_ResponseStub(json_data={"data": [{}]})])
    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=30.0: client_stub,
    )
    runtime._lm_studio_model_cache = None
    with pytest.raises(HTTPException) as missing_model:
        await runtime.resolve_openai_model(api_key="lm-studio")
    assert missing_model.value.status_code == 500

    client_stub = _SequenceAsyncClientStub(responses=[_ResponseStub(json_data={"data": "invalid"})])
    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=30.0: client_stub,
    )
    with pytest.raises(HTTPException) as invalid_models_payload:
        await runtime.resolve_openai_model(api_key="lm-studio")
    assert invalid_models_payload.value.status_code == 500


@pytest.mark.asyncio
async def test_ai_provider_runtime_gemini_suggestion_http_paths(monkeypatch):
    runtime = ia_service.AiProviderRuntime()

    with pytest.raises(HTTPException) as missing_key:
        await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="", response_schema={})
    assert missing_key.value.status_code == 400

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                json_data={
                    "candidates": [{"content": {"parts": [{"text": '{"sugestoes_atributos": []}'}]}}]
                }
            ),
        ),
    )
    assert await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="k", response_schema={}) == {
        "sugestoes_atributos": []
    }

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                json_data={"candidates": [{"content": {"parts": [{"text": "{invalido"}]}}]}
            ),
        ),
    )
    with pytest.raises(HTTPException) as invalid_json:
        await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="k", response_schema={})
    assert invalid_json.value.status_code == 500

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(json_data={"promptFeedback": {"blockReason": "SAFETY"}}),
        ),
    )
    with pytest.raises(HTTPException) as missing_content:
        await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="k", response_schema={})
    assert missing_content.value.status_code == 500
    assert "Feedback do prompt" in missing_content.value.detail

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                status_error=_http_status_error(
                    503,
                    text="unavailable",
                    json_data={"error": {"message": "service unavailable"}},
                )
            ),
        ),
    )
    with pytest.raises(HTTPException) as upstream_error:
        await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="k", response_schema={})
    assert upstream_error.value.status_code == 503
    assert "unavailable" in upstream_error.value.detail.lower()

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(timeout=timeout, error=RuntimeError("timeout")),
    )
    with pytest.raises(HTTPException) as generic_error:
        await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="k", response_schema={})
    assert generic_error.value.status_code == 500

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            error=httpx.ConnectError("offline", request=httpx.Request("POST", "https://example.com")),
        ),
    )
    with pytest.raises(HTTPException) as request_error:
        await runtime.call_gemini_api_for_suggestions(prompt_text="x", api_key="k", response_schema={})
    assert request_error.value.status_code == 503


@pytest.mark.asyncio
async def test_ai_provider_runtime_gemini_text_http_paths(monkeypatch):
    runtime = ia_service.AiProviderRuntime()

    with pytest.raises(HTTPException):
        await runtime.call_gemini_api(prompt_text="x", api_key="")

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                json_data={"candidates": [{"content": {"parts": [{"text": " descricao gemini "}]}}]}
            ),
        ),
    )
    assert await runtime.call_gemini_api(prompt_text="x", api_key="k") == "descricao gemini"

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(timeout=timeout, response=_ResponseStub(json_data={})),
    )
    with pytest.raises(HTTPException) as bad_structure:
        await runtime.call_gemini_api(prompt_text="x", api_key="k")
    assert bad_structure.value.status_code == 500

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(status_error=_http_status_error(429, text="quota estourada")),
        ),
    )
    with pytest.raises(HTTPException) as upstream_error:
        await runtime.call_gemini_api(prompt_text="x", api_key="k")
    assert upstream_error.value.status_code == 429

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(timeout=timeout, error=RuntimeError("network")),
    )
    with pytest.raises(HTTPException) as generic_error:
        await runtime.call_gemini_api(prompt_text="x", api_key="k")
    assert generic_error.value.status_code == 500

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            error=httpx.ConnectError("offline", request=httpx.Request("POST", "https://example.com")),
        ),
    )
    with pytest.raises(HTTPException) as request_error:
        await runtime.call_gemini_api(prompt_text="x", api_key="k")
    assert request_error.value.status_code == 503


def test_ia_generation_runtime_helper_paths(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()

    assert runtime._looks_like_company_timeline_claim("Empresa fundada em 2015") is True
    assert runtime._looks_like_company_timeline_claim("Produto premium para uso severo") is False
    assert runtime._sanitize_generated_description("") == ""
    assert (
        runtime._sanitize_generated_description("Empresa fundada em 2015.")
        == "Empresa fundada em 2015."
    )

    sanitized_titles = runtime._sanitize_title_candidates(
        '1. Titulo Limpo\n2. titulo limpo\n3. www.exemplo.com contato\n4. ok\n5. Fundada em 2010'
    )
    assert sanitized_titles == ["Titulo Limpo"]

    produto = SimpleNamespace(
        nome_base="Reservatorio Comércio Eletrônico 9999",
        nome_chat_api=None,
        marca="Marca 1234567890",
        modelo="Modelo X",
        sku="SKU-1",
        ean="789",
        categoria_original="Suspensao",
        descricao_original="Descricao base",
        descricao_chat_api=None,
    )
    title_candidates = runtime._build_local_title_candidates(produto, num_titulos=3)
    assert title_candidates[0].startswith("Reservatorio")
    assert len(title_candidates) == 3
    description = runtime._build_local_description(produto, tamanho_palavras=80)
    assert "SKU-1" in description
    assert "Descricao base" in description

    class _BrokenUsageRepo:
        def __init__(self, _db):
            pass

        def create_registro_uso_ia(self, registro_uso):
            _ = registro_uso
            raise RuntimeError("db down")

    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _BrokenUsageRepo)
    runtime._registrar_uso_fallback(
        db=object(),
        user_id=1,
        produto_id=2,
        tipo_acao=ia_service.models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        provider_name="openai",
        details="fallback",
    )
    rendered = runtime._render_prompt(
        db=object(),
        nome=ia_service.PromptTemplateName.IA_OPENAI_DESCRIPTION_USER,
        context={"nome_base": "Reservatorio"},
    )
    assert "Reservatorio" in rendered
    assert "Marca:" in rendered


@pytest.mark.asyncio
async def test_ia_generation_runtime_impl_paths_with_provider_and_suggestions(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    produto = SimpleNamespace(
        user_id=1,
        nome_base="Paralama Dianteiro",
        nome_chat_api=None,
        descricao_original="Aplicacao pesada",
        descricao_chat_api=None,
        marca="Acme",
        modelo="Truck",
        sku="PAR-1",
        ean="7890000000001",
        categoria_original="Cabine",
        dynamic_attributes={"cor": "Preto"},
        dados_brutos_web={"extracted_text_content": "conteudo web"},
        product_type=SimpleNamespace(
            attribute_templates=[
                SimpleNamespace(attribute_key="cor"),
                SimpleNamespace(attribute_key="material"),
            ]
        ),
    )
    _ProductRepositoryStub.produto = produto
    _UsageRepositoryStub.created = []

    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    provider_stub = _ProviderWorkflowStub(
        openai_results=[
            "1. Titulo Valido\n2. Fundada em 2010",
            "",
        ],
        gemini_results=["", ""],
    )
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: provider_stub),
    )

    titles = await runtime._gerar_titulos_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert titles == ["Titulo Valido"]

    description = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert "Paralama Dianteiro" in description

    gemini_titles = await runtime._gerar_titulos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert gemini_titles[0].startswith("Paralama Dianteiro")

    gemini_description = await runtime._gerar_descricao_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert "Paralama Dianteiro" in gemini_description

    suggestions = await runtime._sugerir_valores_atributos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
    )
    assert [(item.chave_atributo, item.valor_sugerido) for item in suggestions.sugestoes_atributos] == [
        ("cor", "Azul")
    ]
    assert len(_UsageRepositoryStub.created) >= 5


@pytest.mark.asyncio
async def test_ia_generation_runtime_impl_handles_not_found_auth_and_empty_attribute_cases(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub()),
    )

    _ProductRepositoryStub.produto = None
    with pytest.raises(HTTPException) as not_found:
        await runtime._gerar_titulos_com_openai_impl(
            db=object(),
            produto_id=99,
            user=SimpleNamespace(id=1, is_superuser=False),
            num_titulos=2,
        )
    assert not_found.value.status_code == 404

    _ProductRepositoryStub.produto = SimpleNamespace(
        user_id=10,
        nome_base="Produto",
        nome_chat_api=None,
        descricao_original=None,
        descricao_chat_api=None,
        marca=None,
        modelo=None,
        sku=None,
        ean=None,
        categoria_original=None,
        dynamic_attributes=None,
        dados_brutos_web=None,
        product_type=SimpleNamespace(attribute_templates=[]),
    )
    with pytest.raises(HTTPException) as forbidden:
        await runtime._sugerir_valores_atributos_com_gemini_impl(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=1, is_superuser=False),
        )
    assert forbidden.value.status_code == 403

    _ProductRepositoryStub.produto = SimpleNamespace(
        user_id=1,
        nome_base="Produto",
        nome_chat_api=None,
        descricao_original=None,
        descricao_chat_api=None,
        marca=None,
        modelo=None,
        sku=None,
        ean=None,
        categoria_original=None,
        dynamic_attributes=None,
        dados_brutos_web=None,
        product_type=SimpleNamespace(attribute_templates=[]),
    )
    response = await runtime._sugerir_valores_atributos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
    )
    assert response.sugestoes_atributos == []
    assert response.modelo_ia_utilizado.startswith("gemini")
