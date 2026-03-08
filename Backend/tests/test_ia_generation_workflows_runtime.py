"""Module test ia generation workflows runtime.

Contains backend logic related to test ia generation workflows runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from Backend.testing.runtime_apis import ia_service


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_ai_provider_workflow_usa_runtime_injetado():
        """Run test ai provider workflow usa runtime injetado in this workflow."""
        called = []
    
        class FakeProviderRuntime:
            """Represent fake provider runtime and centralize responsibilities for this module."""
            async def get_openai_api_key(self, db, user):
                """Return openai api key for this workflow."""
                called.append(("openai_key", db, user))
                return "sk-openai"
    
            async def get_gemini_api_key(self, db, user):
                """Return gemini api key for this workflow."""
                called.append(("gemini_key", db, user))
                return "sk-gemini"
    
            async def call_openai_api(self, **kwargs):
                """Run call openai api in this workflow."""
                called.append(("openai_call", kwargs))
                return "ok-openai"
    
            async def call_gemini_api_for_suggestions(self, **kwargs):
                """Run call gemini api for suggestions in this workflow."""
                called.append(("gemini_suggestions", kwargs))
                return {"sugestoes_atributos": []}
    
            async def call_gemini_api(self, **kwargs):
                """Run call gemini api in this workflow."""
                called.append(("gemini_call", kwargs))
                return "ok-gemini"
    
        workflow = ia_service.AiProviderWorkflow(runtime=FakeProviderRuntime())
    
        assert await workflow.get_openai_api_key("db", "u") == "sk-openai"
        assert await workflow.get_gemini_api_key("db", "u") == "sk-gemini"
        assert (
            await workflow.call_openai_api(
                prompt_messages=[{"role": "user", "content": "hi"}],
                api_key="k",
            )
            == "ok-openai"
        )
        assert (
            await workflow.call_gemini_api_for_suggestions(
                prompt_text="texto",
                api_key="k",
                response_schema={},
            )
            == {"sugestoes_atributos": []}
        )
        assert (
            await workflow.call_gemini_api(
                prompt_text="texto",
                api_key="k",
            )
            == "ok-gemini"
        )
    
        assert [item[0] for item in called] == [
            "openai_key",
            "gemini_key",
            "openai_call",
            "gemini_suggestions",
            "gemini_call",
        ]

    @pytest.mark.asyncio
    async def test_ia_generation_workflow_usa_runtime_injetado():
        """Run test ia generation workflow usa runtime injetado in this workflow."""
        called = []
    
        class FakeIARuntime:
            """Represent fake i a runtime and centralize responsibilities for this module."""
            async def gerar_titulos_com_openai(self, **kwargs):
                """Run gerar titulos com openai in this workflow."""
                called.append(("tit_openai", kwargs))
                return ["t1", "t2"]
    
            async def gerar_descricao_com_openai(self, **kwargs):
                """Run gerar descricao com openai in this workflow."""
                called.append(("desc_openai", kwargs))
                return "descricao"
    
            async def gerar_titulos_com_gemini(self, **kwargs):
                """Run gerar titulos com gemini in this workflow."""
                called.append(("tit_gemini", kwargs))
                return ["g1"]
    
            async def gerar_descricao_com_gemini(self, **kwargs):
                """Run gerar descricao com gemini in this workflow."""
                called.append(("desc_gemini", kwargs))
                return "desc-g"
    
            async def sugerir_valores_atributos_com_gemini(self, **kwargs):
                """Run sugerir valores atributos com gemini in this workflow."""
                called.append(("sug_gemini", kwargs))
                return {"ok": True}
    
        workflow = ia_service.IAGenerationWorkflow(runtime=FakeIARuntime())
    
        assert await workflow.gerar_titulos_com_openai("db", 1, "u", 2) == ["t1", "t2"]
        assert await workflow.gerar_descricao_com_openai("db", 1, "u", 50) == "descricao"
        assert await workflow.gerar_titulos_com_gemini("db", 1, "u", 1) == ["g1"]
        assert await workflow.gerar_descricao_com_gemini("db", 1, "u", 60) == "desc-g"
        assert (
            await workflow.sugerir_valores_atributos_com_gemini("db", 1, "u")
            == {"ok": True}
        )
    
        assert [item[0] for item in called] == [
            "tit_openai",
            "desc_openai",
            "tit_gemini",
            "desc_gemini",
            "sug_gemini",
        ]

    @pytest.mark.asyncio
    async def test_ia_generation_runtime_fallback_titulos_sem_chave(monkeypatch):
        """Run test ia generation runtime fallback titulos sem chave in this workflow."""
        runtime = ia_service.IAGenerationRuntime()

        class FakeProviderWorkflow:
            """Represent fake provider workflow and centralize responsibilities for this module."""

            async def get_openai_api_key(self, db, user):
                """Run get openai api key in this workflow."""
                _ = db, user
                return None

        class FakeProductRepository:
            """Represent fake product repository and centralize responsibilities for this module."""

            def __init__(self, db):
                """Run init in this workflow."""
                self._db = db

            def get_produto(self, produto_id):
                """Run get produto in this workflow."""
                _ = produto_id
                return SimpleNamespace(
                    nome_base="Parachoque Dianteiro",
                    nome_chat_api=None,
                    descricao_original="Aplicacao linha pesada",
                    descricao_chat_api=None,
                    marca="Acme",
                    modelo="X1",
                    sku="SKU-123",
                    ean="",
                    categoria_original="Carroceria",
                )

        class FakeUsageRepository:
            """Represent fake usage repository and centralize responsibilities for this module."""

            def __init__(self, db):
                """Run init in this workflow."""
                self._db = db

            def create_registro_uso_ia(self, registro_uso):
                """Run create registro uso ia in this workflow."""
                _ = registro_uso
                return None

        monkeypatch.setattr(
            ia_service.IAGenerationRuntime,
            "_get_ai_provider_workflow",
            staticmethod(lambda: FakeProviderWorkflow()),
        )
        monkeypatch.setattr(ia_service, "ProductRepository", FakeProductRepository)
        monkeypatch.setattr(ia_service, "RegistroUsoIARepository", FakeUsageRepository)

        result = await runtime.gerar_titulos_com_openai(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=99),
            num_titulos=3,
        )

        assert isinstance(result, list)
        assert result
        assert "Parachoque" in result[0]

    @pytest.mark.asyncio
    async def test_ai_provider_runtime_ignora_chave_openai_malformada_e_usa_global_valida(monkeypatch):
        """Ignore malformed saved keys and fallback to a valid global OpenAI key."""
        runtime = ia_service.AiProviderRuntime()
        monkeypatch.setattr(ia_service.settings, "AI_PROVIDER", "openai", raising=False)
        monkeypatch.setattr(
            ia_service.settings,
            "OPENAI_API_KEY",
            "sk-test-12345678901234567890",
            raising=False,
        )

        result = await runtime.get_openai_api_key(
            db=object(),
            user=SimpleNamespace(id=1, chave_openai_pessoal="adminpassword"),
        )

        assert result == "sk-test-12345678901234567890"

    @pytest.mark.asyncio
    async def test_ia_generation_runtime_fallback_descricao_sem_chave(monkeypatch):
        """Run test ia generation runtime fallback descricao sem chave in this workflow."""
        runtime = ia_service.IAGenerationRuntime()

        class FakeProviderWorkflow:
            """Represent fake provider workflow and centralize responsibilities for this module."""

            async def get_gemini_api_key(self, db, user):
                """Run get gemini api key in this workflow."""
                _ = db, user
                return None

        class FakeProductRepository:
            """Represent fake product repository and centralize responsibilities for this module."""

            def __init__(self, db):
                """Run init in this workflow."""
                self._db = db

            def get_produto(self, produto_id):
                """Run get produto in this workflow."""
                _ = produto_id
                return SimpleNamespace(
                    nome_base="Coluna Externa",
                    nome_chat_api=None,
                    descricao_original="Revestimento lateral",
                    descricao_chat_api=None,
                    marca="Acme",
                    modelo="Truck X",
                    sku="COL-890",
                    ean="7890001122334",
                    categoria_original="Cabine",
                )

        class FakeUsageRepository:
            """Represent fake usage repository and centralize responsibilities for this module."""

            def __init__(self, db):
                """Run init in this workflow."""
                self._db = db

            def create_registro_uso_ia(self, registro_uso):
                """Run create registro uso ia in this workflow."""
                _ = registro_uso
                return None

        monkeypatch.setattr(
            ia_service.IAGenerationRuntime,
            "_get_ai_provider_workflow",
            staticmethod(lambda: FakeProviderWorkflow()),
        )
        monkeypatch.setattr(ia_service, "ProductRepository", FakeProductRepository)
        monkeypatch.setattr(ia_service, "RegistroUsoIARepository", FakeUsageRepository)

        result = await runtime.gerar_descricao_com_gemini(
            db=object(),
            produto_id=1,
            user=SimpleNamespace(id=99),
            tamanho_palavras=80,
        )

        assert isinstance(result, str)
        assert "Coluna Externa" in result
        assert "SKU" in result

    def test_ia_generation_runtime_sanitize_description_remove_historico_empresa():
        """Run test ia generation runtime sanitize description remove historico empresa in this workflow."""
        runtime = ia_service.IAGenerationRuntime()
        cleaned = runtime._sanitize_generated_description(
            "Paralama externo com boa resistencia. A Uouu iniciou suas atividades no ano de 2015."
        )

        assert "Paralama externo com boa resistencia" in cleaned
        assert "iniciou suas atividades" not in cleaned.lower()

    def test_ia_generation_runtime_sanitize_titles_remove_historico_empresa():
        """Run test ia generation runtime sanitize titles remove historico empresa in this workflow."""
        runtime = ia_service.IAGenerationRuntime()
        titles = runtime._sanitize_title_candidates(
            "1. Paralama Iveco Stralis Original\n2. Uouu desde 2015 no mercado\n3. Uouu Comercio Eletronico 986 345 430 8205"
        )

        assert any("Paralama Iveco Stralis Original" == title for title in titles)
        assert not any("2015" in title and "mercado" in title.lower() for title in titles)
        assert not any("comercio" in title.lower() for title in titles)
        assert not any("986" in title for title in titles)

test_ai_provider_workflow_usa_runtime_injetado = _TopLevelFunctionSurface.test_ai_provider_workflow_usa_runtime_injetado
test_ia_generation_workflow_usa_runtime_injetado = _TopLevelFunctionSurface.test_ia_generation_workflow_usa_runtime_injetado
test_ia_generation_runtime_fallback_titulos_sem_chave = _TopLevelFunctionSurface.test_ia_generation_runtime_fallback_titulos_sem_chave
test_ai_provider_runtime_ignora_chave_openai_malformada_e_usa_global_valida = _TopLevelFunctionSurface.test_ai_provider_runtime_ignora_chave_openai_malformada_e_usa_global_valida
test_ia_generation_runtime_fallback_descricao_sem_chave = _TopLevelFunctionSurface.test_ia_generation_runtime_fallback_descricao_sem_chave
test_ia_generation_runtime_sanitize_description_remove_historico_empresa = _TopLevelFunctionSurface.test_ia_generation_runtime_sanitize_description_remove_historico_empresa
test_ia_generation_runtime_sanitize_titles_remove_historico_empresa = _TopLevelFunctionSurface.test_ia_generation_runtime_sanitize_titles_remove_historico_empresa





