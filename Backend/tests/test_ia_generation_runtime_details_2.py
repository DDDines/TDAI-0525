"""Extra branch coverage for IA generation runtime internals."""

from __future__ import annotations

import json
import re
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
        openai_result="Resposta OpenAI",
        gemini_result="Resposta Gemini",
        suggestion_result=None,
        suggestion_error=None,
    ):
        self.openai_key = openai_key
        self.gemini_key = gemini_key
        self.openai_result = openai_result
        self.gemini_result = gemini_result
        self.suggestion_result = suggestion_result
        self.suggestion_error = suggestion_error

    async def get_openai_api_key(self, db, user):
        _ = db, user
        return self.openai_key

    async def get_gemini_api_key(self, db, user):
        _ = db, user
        return self.gemini_key

    async def call_openai_api(self, **_kwargs):
        return self.openai_result

    async def call_gemini_api(self, **_kwargs):
        return self.gemini_result

    async def call_gemini_api_for_suggestions(self, **_kwargs):
        if self.suggestion_error:
            raise self.suggestion_error
        return self.suggestion_result


class _OpenAIProviderRuntimeStub:
    async def resolve_openai_model(self, *, api_key, requested_model=None):
        _ = api_key, requested_model
        return "google/gemma-3-12b"

    @staticmethod
    def get_openai_provider_name():
        return "lm_studio"


def _http_status_error(status_code: int, *, text: str, json_data=None):
    request = httpx.Request("POST", "https://example.com")
    if json_data is not None:
        response = httpx.Response(
            status_code,
            request=request,
            content=json.dumps(json_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    else:
        response = httpx.Response(status_code, request=request, text=text)
    return httpx.HTTPStatusError("boom", request=request, response=response)


def _produto_base(**overrides):
    base = {
        "user_id": 1,
        "nome_base": "Paralama Dianteiro",
        "nome_chat_api": None,
        "descricao_original": "Aplicacao pesada",
        "descricao_chat_api": None,
        "marca": "Acme",
        "modelo": "Truck",
        "sku": "PAR-1",
        "ean": "7890000000001",
        "categoria_original": "Cabine",
        "dynamic_attributes": {"cor": "Preto"},
        "dados_brutos_web": {"extracted_text_content": "conteudo web"},
        "product_type": SimpleNamespace(
            attribute_templates=[
                SimpleNamespace(attribute_key="cor"),
                SimpleNamespace(attribute_key="material"),
            ]
        ),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _SearchPatternStub:
    def __init__(self, *, search_result=True):
        self.search_result = search_result

    def sub(self, _replacement, text):
        return text

    def search(self, _text):
        return self.search_result


class _MarkerMatchStub:
    def __init__(self, start_index):
        self._start_index = start_index

    def start(self):
        return self._start_index


class _MarkerPatternStub:
    def __init__(self, *, start_index):
        self.start_index = start_index

    def search(self, _text):
        return _MarkerMatchStub(self.start_index)

    def sub(self, _replacement, text):
        return text


@pytest.mark.asyncio
async def test_ai_provider_runtime_key_resolution_extra_paths(monkeypatch):
    runtime = ia_service.AiProviderRuntime()
    monkeypatch.setattr(ia_service.settings, "AI_PROVIDER", "openai", raising=False)

    monkeypatch.setattr(ia_service.settings, "OPENAI_API_KEY", None, raising=False)
    result = await runtime.get_openai_api_key(
        db=object(),
        user=SimpleNamespace(id=1, chave_openai_pessoal="sk-openai-12345678901234567890"),
    )
    assert result == "sk-openai-12345678901234567890"

    monkeypatch.setattr(ia_service.settings, "OPENAI_API_KEY", "senha-invalida", raising=False)
    result = await runtime.get_openai_api_key(
        db=object(),
        user=SimpleNamespace(id=2, chave_openai_pessoal=None),
    )
    assert result is None

    monkeypatch.setattr(ia_service.settings, "OPENAI_API_KEY", None, raising=False)
    result = await runtime.get_openai_api_key(
        db=object(),
        user=SimpleNamespace(id=6, chave_openai_pessoal=None),
    )
    assert result is None

    monkeypatch.setattr(ia_service.settings, "GOOGLE_GEMINI_API_KEY", None, raising=False)
    result = await runtime.get_gemini_api_key(
        db=object(),
        user=SimpleNamespace(id=3, chave_google_gemini_pessoal="gem-user-key"),
    )
    assert result == "gem-user-key"

    monkeypatch.setattr(ia_service.settings, "GOOGLE_GEMINI_API_KEY", "gem-global", raising=False)
    result = await runtime.get_gemini_api_key(
        db=object(),
        user=SimpleNamespace(id=4, chave_google_gemini_pessoal=None),
    )
    assert result == "gem-global"

    monkeypatch.setattr(ia_service.settings, "GOOGLE_GEMINI_API_KEY", None, raising=False)
    result = await runtime.get_gemini_api_key(
        db=object(),
        user=SimpleNamespace(id=5, chave_google_gemini_pessoal=None),
    )
    assert result is None

    monkeypatch.setattr(ia_service.settings, "AI_PROVIDER", "lm_studio", raising=False)
    monkeypatch.setattr(ia_service.settings, "LM_STUDIO_API_KEY", "", raising=False)
    result = await runtime.get_openai_api_key(
        db=object(),
        user=SimpleNamespace(id=7, chave_openai_pessoal="sk-openai-ignored"),
    )
    assert result == "lm-studio"
    assert runtime.get_openai_provider_name() == "lm_studio"


@pytest.mark.asyncio
async def test_ai_provider_runtime_gemini_suggestion_extra_error_paths(monkeypatch):
    runtime = ia_service.AiProviderRuntime()

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(json_data={}),
        ),
    )
    with pytest.raises(HTTPException) as missing_content:
        await runtime.call_gemini_api_for_suggestions(
            prompt_text="x",
            api_key="gem-key",
            response_schema={},
        )
    assert missing_content.value.status_code == 500
    assert "esperado" in missing_content.value.detail

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                status_error=_http_status_error(
                    503,
                    text="temporarily unavailable",
                    json_data={"error": {"message": "model unavailable"}},
                )
            ),
        ),
    )
    with pytest.raises(HTTPException) as upstream_error:
        await runtime.call_gemini_api_for_suggestions(
            prompt_text="x",
            api_key="gem-key",
            response_schema={},
        )
    assert upstream_error.value.status_code == 503
    assert upstream_error.value.detail == "Erro na API Gemini: model unavailable"

    monkeypatch.setattr(
        ia_service.httpx,
        "AsyncClient",
        lambda timeout=90.0: _AsyncClientStub(
            timeout=timeout,
            response=_ResponseStub(
                status_error=_http_status_error(
                    429,
                    text="quota estourada",
                    json_data={"error": {}},
                )
            ),
        ),
    )
    with pytest.raises(HTTPException) as fallback_error:
        await runtime.call_gemini_api_for_suggestions(
            prompt_text="x",
            api_key="gem-key",
            response_schema={},
        )
    assert fallback_error.value.status_code == 429
    assert "429" in fallback_error.value.detail


@pytest.mark.asyncio
async def test_ia_generation_runtime_public_wrappers_and_workflow_factory(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    captured = []

    async def _fake_desc_openai(**kwargs):
        captured.append(("desc_openai", kwargs))
        return "descricao"

    async def _fake_tit_gemini(**kwargs):
        captured.append(("tit_gemini", kwargs))
        return ["g1"]

    async def _fake_sug_gemini(**kwargs):
        captured.append(("sug_gemini", kwargs))
        return {"ok": True}

    monkeypatch.setattr(runtime, "_gerar_descricao_com_openai_impl", _fake_desc_openai)
    monkeypatch.setattr(runtime, "_gerar_titulos_com_gemini_impl", _fake_tit_gemini)
    monkeypatch.setattr(runtime, "_sugerir_valores_atributos_com_gemini_impl", _fake_sug_gemini)

    assert await runtime.gerar_descricao_com_openai("db", 7, "u", 90) == "descricao"
    assert await runtime.gerar_titulos_com_gemini("db", 7, "u", 2) == ["g1"]
    assert await runtime.sugerir_valores_atributos_com_gemini("db", 7, "u") == {"ok": True}

    workflow = runtime._get_ai_provider_workflow()
    assert isinstance(workflow, ia_service.AiProviderWorkflow)
    assert isinstance(workflow._runtime, ia_service.AiProviderRuntime)
    assert ia_service.IAGenerationRuntime._looks_like_company_timeline_claim("   ") is False

    assert [item[0] for item in captured] == [
        "desc_openai",
        "tit_gemini",
        "sug_gemini",
    ]


def test_ia_generation_runtime_local_helper_edge_paths(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()

    cleaned_description = runtime._sanitize_generated_description(
        "Produto robusto.\n \nEmpresa fundada em 2015."
    )
    assert cleaned_description == "Produto robusto."

    description_without_cta = runtime._sanitize_generated_description(
        "Estrutura resistente para exposicao. Adquira ja e impulsione suas vendas."
    )
    assert description_without_cta == "Estrutura resistente para exposicao."

    prefixed_description = runtime._sanitize_generated_description(
        "Descricao do produto: Paralama reforcado para uso severo."
    )
    assert prefixed_description == "Paralama reforcado para uso severo."

    titles = runtime._sanitize_title_candidates(
        '1. abc\n2. "Paralama contato whatsapp"\n3. Paralama Contato WhatsApp'
    )
    assert titles == ["Paralama"]

    preserved_titles = runtime._sanitize_title_candidates(
        "1. Crown Princess Decor\n2. Tiara Corona Sempre Uma Princesa",
        source_title="Always a Princess Crown Frame",
    )
    assert preserved_titles[0] == "Always a Princess Crown Frame"
    assert "Tiara Corona Sempre Uma Princesa" not in preserved_titles
    assert "Crown Princess Decor" not in preserved_titles

    monkeypatch.setattr(ia_service, "URL_PATTERN", _SearchPatternStub(search_result=True))
    monkeypatch.setattr(ia_service, "EMAIL_PATTERN", _SearchPatternStub(search_result=False))
    monkeypatch.setattr(ia_service, "PHONE_OR_ID_BLOCK_PATTERN", _SearchPatternStub(search_result=False))
    assert runtime._sanitize_title_candidates("Titulo tecnico") == []

    monkeypatch.setattr(ia_service, "URL_PATTERN", _SearchPatternStub(search_result=False))
    monkeypatch.setattr(ia_service, "TITLE_CONTACT_MARKER_PATTERN", _MarkerPatternStub(start_index=8))
    trimmed_titles = runtime._sanitize_title_candidates("Paralama contato loja")
    assert trimmed_titles == ["Paralama"]

    monkeypatch.setattr(ia_service, "TITLE_CONTACT_MARKER_PATTERN", re.compile(r"\b(?:loja|contato)\b", re.IGNORECASE))
    fallback_rotations = runtime._sanitize_title_candidates(
        "1. Descubra o Tier Displayer",
        source_title="Tier Displayer",
        desired_count=3,
    )
    assert fallback_rotations == ["Tier Displayer"]

    short_titles = runtime._build_local_title_candidates(
        _produto_base(nome_base="abc", marca="", modelo="", sku="", categoria_original=""),
        num_titulos=4,
    )
    assert short_titles == ["abc Alta Durabilidade"]

    duplicate_titles = runtime._build_local_title_candidates(
        _produto_base(nome_base="Produto", marca="", modelo="", sku="", categoria_original=""),
        num_titulos=4,
    )
    assert duplicate_titles == ["Produto", "Produto Alta Durabilidade"]

    description = runtime._build_local_description(
        _produto_base(
            descricao_original="Descricao extensa",
            marca="Marca X",
            modelo="Modelo Y",
            sku="SKU-55",
            ean="789123",
            categoria_original="Freios",
        ),
        tamanho_palavras=120,
    )
    assert "Fabricado por Marca X" in description
    assert "Modelo Y" in description
    assert "Categoria de referencia: Freios." in description
    assert "Codigo de identificacao (SKU): SKU-55." in description
    assert "Codigo EAN: 789123." in description
    assert "Informacoes adicionais do catalogo: Descricao extensa." in description
    assert "Antes da venda" in description

    description_minimal = runtime._build_local_description(
        _produto_base(
            nome_base="Item basico",
            marca="",
            modelo="",
            sku="",
            ean="",
            categoria_original="",
            descricao_original="",
            descricao_chat_api="",
        ),
        tamanho_palavras=120,
    )
    assert "Fabricado por" not in description_minimal
    assert "Codigo EAN" not in description_minimal


def test_ia_generation_runtime_title_identity_helper_branches():
    runtime = ia_service.IAGenerationRuntime()

    assert runtime._tokenize_title_identity("contato loja") == []
    assert runtime._build_source_title_variants(
        source_title="Alpha Beta Gamma Delta",
        source_aliases=["alpha beta gamma delta", None],
    ) == ["Alpha Beta Gamma Delta"]

    assert runtime._candidate_preserves_source_identity(
        "Sem contato útil",
        source_variants=["contato loja"],
    ) is False
    assert runtime._candidate_preserves_source_identity(
        "Paralama Dianteiro",
        source_variants=["contato loja"],
    ) is False
    assert runtime._candidate_preserves_source_identity(
        "Paralama",
        source_variants=["Paralama"],
    ) is True
    assert runtime._candidate_is_promotional_or_generic(
        "contato loja",
        source_variants=["Paralama Dianteiro"],
    ) is True

    assert runtime._build_deterministic_title_fallbacks(
        source_variants=["contato loja"],
        desired_count=3,
    ) == []

    assert runtime._build_deterministic_title_fallbacks(
        source_variants=[
            "Alpha Beta Gamma Delta",
            "Delta Alpha Beta Gamma",
            "Alpha Beta",
        ],
        desired_count=4,
    ) == [
        "Alpha Beta Gamma Delta",
        "Delta Alpha Beta Gamma",
        "Gamma Delta Alpha Beta",
        "Alpha Beta",
    ]
    assert runtime._build_deterministic_title_fallbacks(
        source_variants=["Alpha Beta Gamma", ""],
        desired_count=3,
    ) == [
        "Alpha Beta Gamma",
        "Gamma Alpha Beta",
    ]

    assert runtime._reconcile_title_candidates_with_source(
        [],
        source_title="Alpha Beta Gamma",
        desired_count=2,
    ) == [
        "Alpha Beta Gamma",
        "Gamma Alpha Beta",
    ]
    assert runtime._reconcile_title_candidates_with_source(
        [],
        source_title="Alpha Beta Gamma Delta",
        desired_count=3,
    ) == [
        "Alpha Beta Gamma Delta",
        "Delta Alpha Beta Gamma",
        "Gamma Delta Alpha Beta",
    ]


def test_ia_generation_runtime_local_title_marker_cleanup_branch(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    monkeypatch.setattr(ia_service, "TITLE_CONTACT_MARKER_PATTERN", _MarkerPatternStub(start_index=9))

    cleaned_titles = runtime._build_local_title_candidates(
        _produto_base(
            nome_base="Paralama contato loja",
            marca="Marca contato",
            modelo="Modelo X",
            sku="SKU-55",
            categoria_original="Cabine",
        ),
        num_titulos=2,
    )

    assert cleaned_titles[0].startswith("Paralama")
    assert all("contato" not in title.lower() for title in cleaned_titles)


@pytest.mark.asyncio
async def test_ia_generation_runtime_openai_description_additional_paths(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)

    _ProductRepositoryStub.produto = None
    with pytest.raises(HTTPException) as not_found:
        await runtime._gerar_descricao_com_openai_impl(
            db=object(),
            produto_id=99,
            user=SimpleNamespace(id=1, is_superuser=False),
            tamanho_palavras=60,
        )
    assert not_found.value.status_code == 404

    _ProductRepositoryStub.produto = _produto_base()
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(openai_key=None)),
    )
    fallback = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert "Paralama Dianteiro" in fallback
    assert _UsageRepositoryStub.created[-1].status == "FALLBACK"

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(openai_result="   ")),
    )
    rebuilt = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert "Paralama Dianteiro" in rebuilt

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(openai_result="Descricao valida e limpa.")),
    )
    kept = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert kept == "Descricao valida e limpa."


@pytest.mark.asyncio
async def test_ia_generation_runtime_openai_title_fallback_after_empty_llm(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base()
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(openai_result="   ")),
    )

    rebuilt_titles = await runtime._gerar_titulos_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert rebuilt_titles[0].startswith("Paralama Dianteiro")

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(
                openai_result="1. Tiara Corona Sempre Uma Princesa\n2. Moldura Princess Crown"
            )
        ),
    )
    _ProductRepositoryStub.produto = _produto_base(nome_base="Always a Princess Crown Frame")
    preserved_titles = await runtime._gerar_titulos_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert preserved_titles[0] == "Always a Princess Crown Frame"
    assert "Tiara Corona Sempre Uma Princesa" not in preserved_titles


@pytest.mark.asyncio
async def test_ia_generation_runtime_openai_and_gemini_title_fallback_after_identity_cleanup(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base(
        nome_base="",
        nome_chat_api="",
        marca="Acme",
        modelo="Truck",
        sku="PAR-1",
        categoria_original="Cabine",
    )

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(openai_result="1. contato loja\n2. http://example.com")),
    )
    rebuilt_openai_titles = await runtime._gerar_titulos_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert rebuilt_openai_titles[0] == "Produto"
    assert any("Truck" in title or "Acme" in title for title in rebuilt_openai_titles)

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(gemini_result="1. contato loja\n2. http://example.com")),
    )
    rebuilt_gemini_titles = await runtime._gerar_titulos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert rebuilt_gemini_titles[0] == "Produto"
    assert any("Truck" in title or "Acme" in title for title in rebuilt_gemini_titles)


@pytest.mark.asyncio
async def test_ia_generation_runtime_records_openai_compatible_provider_metadata(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base()

    provider_stub = _ProviderWorkflowStub(
        openai_result="1. Titulo tecnico\n2. Titulo tecnico 2",
    )
    provider_stub._runtime = _OpenAIProviderRuntimeStub()
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: provider_stub),
    )

    titles = await runtime._gerar_titulos_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=1,
    )
    description = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )

    assert titles
    assert description
    assert _UsageRepositoryStub.created[-2].provedor_ia == "lm_studio"
    assert _UsageRepositoryStub.created[-2].modelo_ia == "google/gemma-3-12b"
    assert _UsageRepositoryStub.created[-1].provedor_ia == "lm_studio"
    assert _UsageRepositoryStub.created[-1].modelo_ia == "google/gemma-3-12b"


@pytest.mark.asyncio
async def test_ia_generation_runtime_gemini_title_and_description_additional_paths(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)

    _ProductRepositoryStub.produto = None
    with pytest.raises(HTTPException) as title_not_found:
        await runtime._gerar_titulos_com_gemini_impl(
            db=object(),
            produto_id=10,
            user=SimpleNamespace(id=1, is_superuser=False),
            num_titulos=2,
        )
    assert title_not_found.value.status_code == 404

    _ProductRepositoryStub.produto = _produto_base()
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(gemini_key=None)),
    )
    fallback_titles = await runtime._gerar_titulos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert fallback_titles[0].startswith("Paralama Dianteiro")

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(gemini_result="  ")),
    )
    rebuilt_titles = await runtime._gerar_titulos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert rebuilt_titles[0].startswith("Paralama Dianteiro")

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(gemini_result="Titulo Gemini Valido")),
    )
    kept_titles = await runtime._gerar_titulos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert kept_titles == ["Paralama Dianteiro"]

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(gemini_result="1. Tiara Corona Sempre Uma Princesa\n2. Moldura Princess Crown")
        ),
    )
    _ProductRepositoryStub.produto = _produto_base(nome_base="Always a Princess Crown Frame")
    preserved_titles = await runtime._gerar_titulos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        num_titulos=2,
    )
    assert preserved_titles[0] == "Always a Princess Crown Frame"
    assert "Tiara Corona Sempre Uma Princesa" not in preserved_titles

    _ProductRepositoryStub.produto = None
    with pytest.raises(HTTPException) as description_not_found:
        await runtime._gerar_descricao_com_gemini_impl(
            db=object(),
            produto_id=10,
            user=SimpleNamespace(id=1, is_superuser=False),
            tamanho_palavras=60,
        )
    assert description_not_found.value.status_code == 404

    _ProductRepositoryStub.produto = _produto_base()
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(gemini_result="   ")),
    )
    rebuilt_description = await runtime._gerar_descricao_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert "Paralama Dianteiro" in rebuilt_description

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(gemini_result="Descricao Gemini valida.")),
    )
    kept_description = await runtime._gerar_descricao_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert kept_description == "Descricao Gemini valida."


@pytest.mark.asyncio
async def test_ia_generation_runtime_attribute_suggestions_validation_paths(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)

    _ProductRepositoryStub.produto = None
    with pytest.raises(HTTPException) as not_found:
        await runtime._sugerir_valores_atributos_com_gemini_impl(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=1, is_superuser=False),
        )
    assert not_found.value.status_code == 404

    _ProductRepositoryStub.produto = _produto_base(
        dynamic_attributes="nao-dict",
        dados_brutos_web={"extracted_text_content": ""},
    )
    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _ProviderWorkflowStub(suggestion_result={})),
    )
    with pytest.raises(HTTPException) as invalid_payload:
        await runtime._sugerir_valores_atributos_com_gemini_impl(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=1, is_superuser=False),
        )
    assert invalid_payload.value.status_code == 500
    assert "sugestoes_atributos" in invalid_payload.value.detail

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(
                suggestion_result={"sugestoes_atributos": "invalido"}
            )
        ),
    )
    with pytest.raises(HTTPException) as invalid_list:
        await runtime._sugerir_valores_atributos_com_gemini_impl(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=1, is_superuser=False),
        )
    assert invalid_list.value.status_code == 500
    assert "lista" in invalid_list.value.detail.lower()

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(
                suggestion_result={
                    "sugestoes_atributos": [
                        "quebrado",
                        {"chave_atributo": "cor", "valor_sugerido": "Azul"},
                    ]
                }
            )
        ),
    )
    response = await runtime._sugerir_valores_atributos_com_gemini_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
    )
    assert [(item.chave_atributo, item.valor_sugerido) for item in response.sugestoes_atributos] == [
        ("cor", "Azul")
    ]


@pytest.mark.asyncio
async def test_ia_generation_runtime_attribute_suggestions_error_paths(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base(dados_brutos_web="nao-dict")

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(
                suggestion_error=HTTPException(status_code=429, detail="quota estourada")
            )
        ),
    )
    with pytest.raises(HTTPException) as upstream_error:
        await runtime._sugerir_valores_atributos_com_gemini_impl(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=1, is_superuser=False),
        )
    assert upstream_error.value.status_code == 429
    assert _UsageRepositoryStub.created[-1].status == "FALHA"

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(
                suggestion_error=RuntimeError("boom")
            )
        ),
    )
    with pytest.raises(HTTPException) as generic_error:
        await runtime._sugerir_valores_atributos_com_gemini_impl(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=1, is_superuser=False),
        )
    assert generic_error.value.status_code == 500
    assert "sugestoes de atributos" in generic_error.value.detail.lower()
