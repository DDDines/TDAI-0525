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

    @staticmethod
    def get_lm_studio_description_word_target(requested_words: int) -> int:
        return min(max(40, int(requested_words or 40)), 50)

    @staticmethod
    def get_lm_studio_description_max_tokens(requested_words: int) -> int:
        _ = requested_words
        return 150


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


def test_ia_generation_runtime_filters_aliases_and_prefers_identity_preserving_titles():
    aliases = ia_service.IAGenerationRuntime._filter_prompt_source_aliases(
        primary_source="Tela Central do Painel Superior",
        aliases=[
            "Tela Central do Painel Superior Scania",
            "Vidro Porta 111 Scania",
            "Tela Central do Painel Superior Ref 236331",
        ],
    )
    assert aliases == [
        "Tela Central do Painel Superior Scania",
        "Tela Central do Painel Superior Ref 236331",
    ]

    prompt_context = {
        "source_title": "Tela Central do Painel Superior",
        "source_aliases": aliases,
        "fallback_titles": [
            "Tela Central do Painel Superior",
            "Tela Central do Painel Superior Scania",
            "Tela Central do Painel Superior Ref 236331",
            "Tela Central do Painel Superior Vidro",
        ],
        "referencia": "236331",
        "marca": "Scania",
        "material": "Vidro",
        "aplicacao": "G/R SERIE 5 ATE 2009",
    }

    selected = ia_service.IAGenerationRuntime._select_final_title_candidates(
        prompt_context=prompt_context,
        llm_titles=[
            "Vidro Porta 111 Scania 236331",
            "Tela Central do Painel Superior Scania",
        ],
        desired_count=4,
    )

    assert selected[0] == "Tela Central do Painel Superior"
    assert "Vidro Porta 111 Scania 236331" not in selected
    assert "Tela Central do Painel Superior Ref 236331" in selected


def test_ia_generation_runtime_deprioritizes_raw_application_dump_titles():
    prompt_context = {
        "source_title": "Tela Central do Painel Superior",
        "source_aliases": [
            "Tela Central do Painel Superior Scania",
            "Tela Central do Painel Superior Ref 236331",
        ],
        "fallback_titles": [
            "Tela Central do Painel Superior",
            "Tela Central do Painel Superior Scania",
            "Tela Central do Painel Superior Ref 236331",
            "Tela Central do Painel Superior G/R SERIE 5 ATE 2009",
            "Tela Central do Painel Superior Vidro",
            "Scania Tela Central do Painel Superior",
        ],
        "referencia": "236331",
        "marca": "Scania",
        "material": "Vidro",
        "aplicacao": "G/R SERIE 5 ATE 2009",
    }

    selected = ia_service.IAGenerationRuntime._select_final_title_candidates(
        prompt_context=prompt_context,
        llm_titles=[],
        desired_count=5,
    )

    assert "Tela Central do Painel Superior G/R SERIE 5 ATE 2009" not in selected
    assert any(item in selected for item in ["Tela Central do Painel Superior Vidro", "Scania Tela Central do Painel Superior"])


def test_ia_generation_runtime_rejects_bare_reference_title_variants():
    selected = ia_service.IAGenerationRuntime._select_final_title_candidates(
        prompt_context={
            "source_title": "Bomba de combustivel Bosch 12V flex",
            "source_aliases": [
                "Bomba de combustivel Bosch 12V flex Aco",
                "Bomba de combustivel Bosch 12V flex Ref SMOKE-PUMP-IA",
            ],
            "fallback_titles": [
                "Bomba de combustivel Bosch 12V flex",
                "Bomba de combustivel Bosch 12V flex Aco",
                "Bomba de combustivel Bosch 12V flex Ref SMOKE-PUMP-IA",
            ],
            "referencia": "SMOKE-PUMP-IA",
            "marca": "Bosch",
            "material": "Aco",
            "aplicacao": "motores flex",
        },
        llm_titles=[
            "Bomba de combustivel Bosch 12V flex",
            "Bomba de combustivel Bosch 12V flex Ref",
            "Bomba de combustivel Bosch 12V flex Aco",
        ],
        desired_count=3,
    )

    assert "Bomba de combustivel Bosch 12V flex Ref" not in selected
    assert "Bomba de combustivel Bosch 12V flex Ref SMOKE-PUMP-IA" in selected
    assert "Bomba de combustivel Bosch 12V flex Aco" not in selected


def test_ia_generation_runtime_preserves_fone_product_titles():
    assert (
        ia_service.IAGenerationRuntime._clean_single_title_candidate(
            "Fone Bluetooth JBL Tune 510BT Preto"
        )
        == "Fone Bluetooth JBL Tune 510BT Preto"
    )


def test_ia_generation_runtime_promotes_diverse_title_variant_categories():
    selected = ia_service.IAGenerationRuntime._select_final_title_candidates(
        prompt_context={
            "source_title": "Bomba de combustivel Bosch 12V flex",
            "source_aliases": [
                "Bomba de combustivel Bosch 12V flex Ref SMOKE-PUMP-IA",
                "Bomba de combustivel Bosch 12V flex motores flex",
                "Bomba de combustivel Bosch 12V flex Aco",
                "Bomba de combustivel Bosch 12V flex Bosch",
            ],
            "fallback_titles": [
                "Bomba de combustivel Bosch 12V flex",
                "Bomba de combustivel Bosch 12V flex Ref SMOKE-PUMP-IA",
                "Bomba de combustivel Bosch 12V flex motores flex",
                "Bomba de combustivel Bosch 12V flex Aco",
                "Bomba de combustivel Bosch 12V flex Bosch",
            ],
            "referencia": "SMOKE-PUMP-IA",
            "marca": "Bosch",
            "material": "Aco",
            "aplicacao": "motores flex",
        },
        llm_titles=[
            "Bomba de combustivel Bosch 12V flex",
            "Bomba de combustivel Bosch 12V flex Bosch",
            "Bomba de combustivel Bosch 12V flex Aco",
        ],
        desired_count=3,
    )

    assert selected[0] == "Bomba de combustivel Bosch 12V flex"
    assert "Bomba de combustivel Bosch 12V flex Ref SMOKE-PUMP-IA" in selected
    assert "Bomba de combustivel Bosch 12V flex motores flex" in selected
    assert "Bomba de combustivel Bosch 12V flex Aco" not in selected


def test_ia_generation_runtime_prefers_content_variant_over_composite_material():
    selected = ia_service.IAGenerationRuntime._select_final_title_candidates(
        prompt_context={
            "source_title": "Kit de Embreagem Luk Cambio Manual",
            "source_aliases": [
                "Kit de Embreagem Luk Cambio Manual Ref 62030847",
                "Kit de Embreagem Luk Cambio Manual disco plato e rolamento",
                "Kit de Embreagem Luk Cambio Manual aco e composto de friccao",
            ],
            "fallback_titles": [
                "Kit de Embreagem Luk Cambio Manual",
                "Kit de Embreagem Luk Cambio Manual Ref 62030847",
                "Kit de Embreagem Luk Cambio Manual disco plato e rolamento",
                "Kit de Embreagem Luk Cambio Manual aco e composto de friccao",
            ],
            "referencia": "62030847",
            "marca": "Luk",
            "material": "aco e composto de friccao",
            "aplicacao": "cambio manual",
            "conteudo": "disco plato e rolamento",
        },
        llm_titles=[
            "Kit de Embreagem Luk Cambio Manual",
            "Kit de Embreagem Luk Cambio Manual aco e composto de friccao",
        ],
        desired_count=3,
    )

    assert selected[0] == "Kit de Embreagem Luk Cambio Manual"
    assert "Kit de Embreagem Luk Cambio Manual Ref 62030847" in selected
    assert "Kit de Embreagem Luk Cambio Manual disco plato e rolamento" in selected
    assert "Kit de Embreagem Luk Cambio Manual aco e composto de friccao" not in selected


def test_ia_generation_runtime_uses_model_code_as_reference_signal_when_reference_missing():
    runtime = ia_service.IAGenerationRuntime

    assert runtime._resolve_title_reference_signal(referencia="", modelo="0580454094") == "0580454094"
    assert runtime._resolve_title_reference_signal(referencia="", modelo="Ultinon Vision") == ""

    selected = runtime._select_final_title_candidates(
        prompt_context={
            "source_title": "Filtro de Ar Primario Mann C27010",
            "source_aliases": [
                "Filtro de Ar Primario Mann C27010 Ref C27010",
                "Filtro de Ar Primario Mann C27010 linha pesada",
                "Filtro de Ar Primario Mann C27010 Mann",
            ],
            "fallback_titles": [
                "Filtro de Ar Primario Mann C27010",
                "Filtro de Ar Primario Mann C27010 Ref C27010",
                "Filtro de Ar Primario Mann C27010 linha pesada",
                "Filtro de Ar Primario Mann C27010 Mann",
            ],
            "referencia": "C27010",
            "modelo": "C27010",
            "marca": "Mann",
            "material": "papel filtrante",
            "aplicacao": "linha pesada",
        },
        llm_titles=[
            "Filtro de Ar Primario Mann C27010",
            "Filtro de Ar Primario Mann C27010 linha pesada",
            "Filtro de Ar Primario Mann C27010 Mann",
        ],
        desired_count=3,
    )

    assert selected[0] == "Filtro de Ar Primario Mann C27010"
    assert "Filtro de Ar Primario Mann C27010 Ref C27010" in selected
    assert "Filtro de Ar Primario Mann C27010 Mann" not in selected


def test_ia_generation_runtime_preserves_numeric_reference_but_removes_contact_number():
    runtime = ia_service.IAGenerationRuntime

    assert (
        runtime._clean_single_title_candidate("Bomba de combustivel Bosch 12V flex Ref 0580454622")
        == "Bomba de combustivel Bosch 12V flex Ref 0580454622"
    )
    assert (
        runtime._clean_single_title_candidate("Bomba de combustivel Bosch 12V Ligue 11 99999-0000")
        == "Bomba de combustivel Bosch 12V"
    )


def test_ia_generation_runtime_finalizes_description_with_product_heading():
    finalized = ia_service.IAGenerationRuntime._finalize_structured_description(
        "Resumo tecnico:\nDescricao objetiva.\nAplicacao:\nScania",
        product_name="Tela Central do Painel Superior",
        fallback_text="Tela Central do Painel Superior\n\nResumo tecnico:\nFallback",
    )

    assert finalized.startswith("Tela Central do Painel Superior\n\nResumo tecnico:")


def test_ia_generation_runtime_finalizer_strips_redundant_product_name_from_summary():
    finalized = ia_service.IAGenerationRuntime._finalize_structured_description(
        (
            "Lampada LED Philips H7 6500K 12V\n\n"
            "Resumo tecnico:\n"
            "Lampada LED Philips H7 6500K 12V Lampada LED H7 para substituicao automotiva.\n"
            "Aplicacao:\nfarol automotivo"
        ),
        product_name="Lampada LED Philips H7 6500K 12V",
        fallback_text=(
            "Lampada LED Philips H7 6500K 12V\n\n"
            "Resumo tecnico:\nFallback tecnico.\n"
            "Aplicacao:\nfarol automotivo"
        ),
    )

    assert "Resumo tecnico:\nLampada LED H7 para substituicao automotiva." in finalized
    assert "Resumo tecnico:\nLampada LED Philips H7 6500K 12V Lampada LED H7" not in finalized


def test_ia_generation_runtime_finalizer_strips_base_name_from_summary_prefix():
    finalized = ia_service.IAGenerationRuntime._finalize_structured_description(
        (
            "Filtro de Ar Primario Mann C27010\n\n"
            "Resumo tecnico:\n"
            "Filtro de Ar Primario Mann C27010 Elemento filtrante primario para retencao de particulas em operacao severa.\n"
            "Aplicacao:\nlinha pesada"
        ),
        product_name="Filtro de Ar Primario Mann C27010",
        fallback_text=(
            "Filtro de Ar Primario Mann C27010\n\n"
            "Resumo tecnico:\nFallback tecnico.\n"
            "Aplicacao:\nlinha pesada"
        ),
    )

    assert "Resumo tecnico:\nElemento filtrante primario para retencao de particulas em operacao severa." in finalized
    assert "Resumo tecnico:\nFiltro de Ar Primario Mann C27010 Elemento" not in finalized


def test_ia_generation_runtime_parses_inline_description_headings():
    preamble, sections = ia_service.IAGenerationRuntime._parse_description_sections(
        (
            "Bomba de combustivel Bosch 12V flex\n"
            "Resumo tecnico: Bomba eletrica com pressao estavel.\n"
            "Aplicacao: motores flex\n"
            "Referencia: SMOKE-PUMP-IA\n"
            "Material: Aco"
        )
    )

    assert preamble == ["Bomba de combustivel Bosch 12V flex"]
    assert sections == [
        ("Resumo tecnico:", ["Bomba eletrica com pressao estavel."]),
        ("Aplicacao:", ["motores flex"]),
        ("Referencia:", ["SMOKE-PUMP-IA"]),
        ("Material:", ["Aco"]),
    ]


def test_ia_generation_runtime_replaces_drifted_summary_with_fallback_summary():
    finalized = ia_service.IAGenerationRuntime._finalize_structured_description(
        (
            "Tela Central do Painel Superior\n\n"
            "Resumo tecnico:\nVidro para porta da linha 111 da Scania.\n"
            "Aplicacao:\nG/R SERIE 5 ATE 2009"
        ),
        product_name="Tela Central do Painel Superior",
        fallback_text=(
            "Tela Central do Painel Superior\n\n"
            "Resumo tecnico:\nTela Central do Painel Superior com aplicacao em G/R SERIE 5 ATE 2009.\n"
            "Aplicacao:\nG/R SERIE 5 ATE 2009"
        ),
    )

    assert "Vidro para porta" not in finalized
    assert "Tela Central do Painel Superior com aplicacao em G/R SERIE 5 ATE 2009." in finalized


def test_ia_generation_runtime_replaces_low_value_summary_with_stronger_fallback_summary():
    finalized = ia_service.IAGenerationRuntime._finalize_structured_description(
        (
            "Tier Displayer\n\n"
            "Resumo tecnico:\n"
            "Tier Displayer e um componente para exibicao em camadas.\n"
            "Sua funcao especifica depende do contexto de uso nao automotivo.\n"
            "Aplicacao:\nNao informado."
        ),
        product_name="Tier Displayer",
        fallback_text=(
            "Tier Displayer\n\n"
            "Resumo tecnico:\n"
            "Expositor em camadas para organizacao e apresentacao visual de itens.\n"
            "Aplicacao:\nNao informado."
        ),
    )

    assert "depende do contexto" not in finalized
    assert "Resumo tecnico:\nExpositor em camadas para organizacao e apresentacao visual de itens." in finalized


def test_ia_generation_runtime_drops_encoded_english_scrape_fragments_from_description():
    sanitized = ia_service.IAGenerationRuntime._sanitize_generated_description(
        (
            "Winter Wishes Snowman Figures - 2 Assorted\n\n"
            "Resumo tecnico:\n"
            "This%20collection%2C%20including%20the%20Lit%20Snowman%20Scene%20Glass%20Ornaments%20-%202%20Assorted%2C%20represents%20winter%20landscapes.\n"
            "Destaques tecnicos:\n"
            "- URL da fonte"
        )
    )

    assert "This%20collection" not in sanitized
    assert "This collection" not in sanitized
    assert "URL da fonte" not in sanitized


def test_ia_generation_runtime_detects_truncated_description_tails():
    assert ia_service.IAGenerationRuntime._description_tail_looks_truncated(
        "Lampada LED Philips H7 6500K 12V\nDestaques tecnicos:\n- Lampada LED Philips H7 6500K"
    )
    assert ia_service.IAGenerationRuntime._description_tail_looks_truncated(
        "Bomba de combustivel Bosch 12V flex\nEspecificacoes tecnicas:\n- Material: Aco Destaques"
    )
    assert not ia_service.IAGenerationRuntime._description_tail_looks_truncated(
        "Lampada LED Philips H7 6500K 12V\nDestaques tecnicos:\n- Lampada LED Philips H7 6500K 12V."
    )


def test_ia_generation_runtime_builds_highlights_from_summary_lines():
    highlights = ia_service.IAGenerationRuntime._build_highlight_lines_from_summary(
        [
            "Bomba de combustivel Bosch 12V flex fornece pressao estavel e opera com baixo nivel de ruido.",
            "Projetada para motores flex.",
        ],
        fallback_lines=["- fallback antigo"],
    )

    assert highlights == [
        "- Bomba de combustivel Bosch 12V flex fornece pressao estavel e opera com baixo nivel de ruido.",
        "- Projetada para motores flex.",
    ]


def test_ia_generation_runtime_builds_stable_fallback_prompt_context():
    context = ia_service.IAGenerationRuntime._build_generation_prompt_context(
        db_produto=_produto_base(
            nome_base="Bomba de combustivel Bosch 12V flex",
            descricao_original=(
                "Bomba de combustivel eletrica 12V para injecao eletronica com pressao estavel, "
                "baixo ruido e aplicacao em motores flex."
            ),
            marca="Bosch",
            modelo="F000TE1773223875B",
            sku="SMOKE-PUMP-IA-TESTE",
            dynamic_attributes={"voltagem": "12V", "aplicacao": "motores flex", "material": "Aco"},
        ),
        tamanho_palavras=50,
        minimum_tamanho_palavras=40,
    )

    assert context["descricao"].startswith("Bomba de combustivel Bosch 12V flex\n\nResumo tecnico:")
    assert "\nAplicacao:\n" in context["fallback_description"]
    assert "\nDestaques tecnicos:\n" in context["fallback_description"]
    assert "- Material: Aco" in context["specs"]
    assert context["categoria"] == "Cabine"
    assert context["segmento_produto"] == "automotivo"


def test_ia_generation_runtime_marks_non_automotive_prompt_context_and_guardrail():
    context = ia_service.IAGenerationRuntime._build_generation_prompt_context(
        db_produto=_produto_base(
            nome_base="Princess Frame",
            descricao_original="Porta-retrato decorativo para fotos infantis.",
            marca="",
            modelo="",
            sku="",
            categoria_original="Decoracao Infantil",
            dynamic_attributes={},
            dados_brutos_web={"extracted_text_content": "Princess Frame decorative picture frame"},
        ),
        tamanho_palavras=50,
        minimum_tamanho_palavras=40,
    )

    assert context["categoria"] == "Decoracao Infantil"
    assert context["segmento_produto"] == "geral"
    assert "Princess Frame Decoracao Infantil" in context["source_aliases"]
    assert "Princess Frame Moldura" in context["source_aliases"]
    assert "nao pertence ao segmento automotivo" in ia_service.IAGenerationRuntime._build_domain_guardrail_text(
        prompt_context=context,
        target="description",
    ).lower()


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
    assert fallback_rotations == ["Tier Displayer", "Displayer Tier"]

    short_titles = runtime._build_local_title_candidates(
        _produto_base(nome_base="abc", marca="", modelo="", sku="", categoria_original=""),
        num_titulos=4,
    )
    assert short_titles == ["Produto"]

    duplicate_titles = runtime._build_local_title_candidates(
        _produto_base(nome_base="Produto", marca="", modelo="", sku="", categoria_original=""),
        num_titulos=4,
    )
    assert duplicate_titles == ["Produto"]

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
    assert description.startswith("Paralama Dianteiro")
    assert "Resumo tecnico:" in description
    assert "Aplicacao:" in description
    assert "Referencia:" in description
    assert "SKU: SKU-55" in description
    assert "EAN: 789123" in description

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
    assert "EAN:" not in description_minimal


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
    assert runtime._candidate_is_promotional_or_generic(
        "Jogo de Pastilhas de Freio TRW Dianteira linha leve",
        source_variants=["Jogo de Pastilhas de Freio TRW Dianteira"],
    ) is False

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
    assert runtime._build_deterministic_title_fallbacks(
        source_variants=["Princess Frame"],
        desired_count=3,
    ) == [
        "Princess Frame",
        "Frame Princess",
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


def test_ia_generation_runtime_keeps_three_titles_for_short_generic_source_names():
    selected = ia_service.IAGenerationRuntime._select_final_title_candidates(
        prompt_context={
            "source_title": "Princess Frame",
            "source_aliases": ["Princess Frame Decoracao Infantil", "Princess Frame Moldura"],
            "fallback_titles": ["Princess Frame", "Princess Frame Decoracao Infantil", "Princess Frame Moldura"],
            "referencia": "",
            "marca": "",
            "material": "",
            "aplicacao": "",
            "conteudo": "",
            "categoria": "Decoracao Infantil",
        },
        llm_titles=[
            "Princess Frame",
            "Princess Frame - Acessorio",
            "Princess Frame Original",
        ],
        desired_count=3,
    )

    assert selected[0] == "Princess Frame"
    assert "Princess Frame Moldura" in selected
    assert "Princess Frame Original" not in selected
    assert len(selected) == 3


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
    assert kept.startswith("Paralama Dianteiro")
    assert "Resumo tecnico:" in kept

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(
            lambda: _ProviderWorkflowStub(
                openai_result=(
                    "Paralama Dianteiro\n"
                    "Resumo tecnico:\n"
                    "Paralama dianteiro em aco para reposicao automotiva.\n"
                    "Especificacoes tecnicas:\n"
                    "- Press"
                )
            )
        ),
    )
    repaired = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=60,
    )
    assert "Paralama dianteiro em aco para reposicao automotiva." in repaired
    assert "- Press" not in repaired
    assert "Conteudo da embalagem:" in repaired


@pytest.mark.asyncio
async def test_ia_generation_runtime_openai_description_uses_compact_lm_studio_profile(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base()

    captured = {}

    class _WorkflowStub:
        def __init__(self):
            self._runtime = _OpenAIProviderRuntimeStub()

        async def get_openai_api_key(self, db, user):
            _ = db, user
            return "lm-studio"

        async def call_openai_api(self, **kwargs):
            captured.update(kwargs)
            return "Descricao valida."

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _WorkflowStub()),
    )

    result = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=140,
    )

    assert result.startswith("Paralama Dianteiro")
    assert captured["max_tokens"] == 150
    assert "50" in captured["prompt_messages"][0]["content"]
    assert "Conteudo da embalagem:" in result
    assert "\nAplicacao:\n" in result


@pytest.mark.asyncio
async def test_ia_generation_runtime_openai_description_normalizes_inline_lm_studio_sections(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base(
        nome_base="Bomba de combustivel Bosch 12V flex",
        descricao_original=(
            "Bomba de combustivel eletrica 12V para injecao eletronica com pressao estavel, "
            "baixo ruido e aplicacao em motores flex."
        ),
        marca="Bosch",
        modelo="F000TE1773222765B",
        sku="SMOKE-PUMP-IA-TESTE",
        dynamic_attributes={"material": "Aco"},
    )

    class _WorkflowStub:
        def __init__(self):
            self._runtime = _OpenAIProviderRuntimeStub()

        async def get_openai_api_key(self, db, user):
            _ = db, user
            return "lm-studio"

        async def call_openai_api(self, **kwargs):
            _ = kwargs
            return (
                "Bomba de combustivel Bosch 12V flex\n"
                "Resumo tecnico: Bomba de combustivel Bosch 12V flex fornece combustivel para injecao eletronica.\n"
                "Aplicacao: motores flex\n"
                "Referencia: SMOKE-PUMP-IA-TESTE\n"
                "Material: Aco Destaques\n"
                "Resumo tecnico:\n"
                "Garante pressao estavel e opera com baixo nivel de ruido."
            )

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _WorkflowStub()),
    )

    result = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=140,
    )

    assert result.startswith("Bomba de combustivel Bosch 12V flex\nResumo tecnico:")
    assert result.count("Resumo tecnico:") == 1
    assert "Resumo tecnico: Bomba de combustivel" not in result
    assert "\nAplicacao:\n" in result
    assert "\nReferencia:\n" in result
    assert "\nMaterial:\nAco" in result
    assert "Aco Destaques" not in result
    assert "\nDestaques tecnicos:\n- Bomba de combustivel Bosch 12V flex fornece combustivel para injecao eletronica." in result


@pytest.mark.asyncio
async def test_ia_generation_runtime_openai_description_lm_studio_timeout_falls_back(monkeypatch):
    runtime = ia_service.IAGenerationRuntime()
    _UsageRepositoryStub.created = []
    monkeypatch.setattr(ia_service, "ProductRepository", _ProductRepositoryStub)
    monkeypatch.setattr(ia_service, "RegistroUsoIARepository", _UsageRepositoryStub)
    _ProductRepositoryStub.produto = _produto_base()

    class _WorkflowStub:
        def __init__(self):
            self._runtime = _OpenAIProviderRuntimeStub()

        async def get_openai_api_key(self, db, user):
            _ = db, user
            return "lm-studio"

        async def call_openai_api(self, **kwargs):
            _ = kwargs
            raise HTTPException(status_code=503, detail="timeout")

    monkeypatch.setattr(
        ia_service.IAGenerationRuntime,
        "_get_ai_provider_workflow",
        staticmethod(lambda: _WorkflowStub()),
    )

    fallback = await runtime._gerar_descricao_com_openai_impl(
        db=object(),
        produto_id=1,
        user=SimpleNamespace(id=1, is_superuser=False),
        tamanho_palavras=140,
    )

    assert fallback.startswith("Paralama Dianteiro")
    assert _UsageRepositoryStub.created[-1].status == "FALLBACK"
    assert _UsageRepositoryStub.created[-1].provedor_ia == "lm_studio"


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
    assert len(rebuilt_openai_titles) >= 1

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
    assert len(rebuilt_gemini_titles) >= 1


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
    assert kept_titles[0] == "Paralama Dianteiro"
    assert len(kept_titles) == 2

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
    assert kept_description.startswith("Paralama Dianteiro")
    assert "Resumo tecnico:" in kept_description


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
