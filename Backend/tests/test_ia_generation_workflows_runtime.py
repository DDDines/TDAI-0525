from __future__ import annotations

import pytest

from Backend.testing.runtime_apis import ia_service


@pytest.mark.asyncio
async def test_ai_provider_workflow_usa_runtime_injetado():
    called = []

    class FakeProviderRuntime:
        async def get_openai_api_key(self, db, user):
            called.append(("openai_key", db, user))
            return "sk-openai"

        async def get_gemini_api_key(self, db, user):
            called.append(("gemini_key", db, user))
            return "sk-gemini"

        async def call_openai_api(self, **kwargs):
            called.append(("openai_call", kwargs))
            return "ok-openai"

        async def call_gemini_api_for_suggestions(self, **kwargs):
            called.append(("gemini_suggestions", kwargs))
            return {"sugestoes_atributos": []}

        async def call_gemini_api(self, **kwargs):
            called.append(("gemini_call", kwargs))
            return "ok-gemini"

    workflow = ia_service._AiProviderWorkflow(runtime=FakeProviderRuntime())

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
    called = []

    class FakeIARuntime:
        async def gerar_titulos_com_openai(self, **kwargs):
            called.append(("tit_openai", kwargs))
            return ["t1", "t2"]

        async def gerar_descricao_com_openai(self, **kwargs):
            called.append(("desc_openai", kwargs))
            return "descricao"

        async def gerar_titulos_com_gemini(self, **kwargs):
            called.append(("tit_gemini", kwargs))
            return ["g1"]

        async def gerar_descricao_com_gemini(self, **kwargs):
            called.append(("desc_gemini", kwargs))
            return "desc-g"

        async def sugerir_valores_atributos_com_gemini(self, **kwargs):
            called.append(("sug_gemini", kwargs))
            return {"ok": True}

    workflow = ia_service._IAGenerationWorkflow(runtime=FakeIARuntime())

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


