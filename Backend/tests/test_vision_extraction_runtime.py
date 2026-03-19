"""Tests for VisionExtractionRuntime — covers error paths and happy paths for GPT-4o Vision extraction."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from Backend.testing.runtime_apis import VisionExtractionRuntime


class _TopLevelFunctionSurface:
    """Centralize all VisionExtractionRuntime test functions as static methods."""

    @pytest.mark.asyncio
    async def test_vision_extraction_sem_api_key_retorna_erro():
        """When no API key is available, returns list with erro_processamento_pdf key."""
        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY=""))

        with patch(
            "Backend.core.config.settings",
            SimpleNamespace(OPENAI_API_KEY=""),
        ):
            result = await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=None,
            )

        assert len(result) == 1
        assert "erro_processamento_pdf" in result[0]

    @pytest.mark.asyncio
    async def test_vision_extraction_openai_nao_instalado_retorna_erro():
        """When openai is not installed, returns list with erro_processamento_pdf key."""
        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY="sk-test"))

        original = sys.modules.get("openai")
        sys.modules["openai"] = None  # Cause ImportError on 'from openai import AsyncOpenAI'

        try:
            result = await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=None,
            )
        finally:
            if original is None:
                sys.modules.pop("openai", None)
            else:
                sys.modules["openai"] = original

        assert len(result) == 1
        assert "erro_processamento_pdf" in result[0]

    @pytest.mark.asyncio
    async def test_vision_extraction_api_error_retorna_erro():
        """When AsyncOpenAI raises an exception during API call, returns error list."""
        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY="sk-test"))

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API timeout"))

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=None,
            )

        assert len(result) == 1
        assert "erro_processamento_pdf" in result[0]
        assert "API timeout" in result[0]["erro_processamento_pdf"]

    @pytest.mark.asyncio
    async def test_vision_extraction_json_invalido_retorna_lista_vazia():
        """When API response is not valid JSON, returns empty list."""
        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY="sk-test"))

        mock_message = SimpleNamespace(content="not valid json {{{{")
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=None,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_vision_extraction_retorna_produtos():
        """When API returns valid JSON with products, returns product list."""
        import json

        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY="sk-test"))

        payload = json.dumps({"produtos": [{"nome_base": "Produto A", "sku_original": "P001"}]})
        mock_message = SimpleNamespace(content=payload)
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=None,
            )

        assert len(result) == 1
        assert result[0]["nome_base"] == "Produto A"
        assert result[0]["sku_original"] == "P001"

    @pytest.mark.asyncio
    async def test_vision_extraction_usa_chave_do_usuario():
        """When user has chave_openai_pessoal, that key is used to instantiate AsyncOpenAI."""
        import json

        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY="sk-system"))

        user = SimpleNamespace(chave_openai_pessoal="sk-user-personal")

        payload = json.dumps({"produtos": [{"nome_base": "Produto B", "sku_original": "P002"}]})
        mock_message = SimpleNamespace(content=payload)
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        captured_keys: list = []

        def fake_async_openai(*, api_key):
            captured_keys.append(api_key)
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            return mock_client

        with patch("openai.AsyncOpenAI", side_effect=fake_async_openai):
            await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=user,
            )

        assert captured_keys == ["sk-user-personal"]

    @pytest.mark.asyncio
    async def test_vision_extraction_descarta_produtos_sem_nome():
        """Products with empty nome_base are filtered out from results."""
        import json

        runtime = VisionExtractionRuntime(settings=SimpleNamespace(OPENAI_API_KEY="sk-test"))

        payload = json.dumps({
            "produtos": [
                {"nome_base": "", "sku_original": "P001"},
                {"nome_base": "Produto Valido", "sku_original": "P002"},
                {"nome_base": None, "sku_original": "P003"},
            ]
        })
        mock_message = SimpleNamespace(content=payload)
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await runtime.extrair_pagina_com_gpt4_vision(
                page_image_data_url="data:image/png;base64,abc",
                page_text=None,
                user=None,
            )

        assert len(result) == 1
        assert result[0]["nome_base"] == "Produto Valido"


test_vision_extraction_sem_api_key_retorna_erro = _TopLevelFunctionSurface.test_vision_extraction_sem_api_key_retorna_erro
test_vision_extraction_openai_nao_instalado_retorna_erro = _TopLevelFunctionSurface.test_vision_extraction_openai_nao_instalado_retorna_erro
test_vision_extraction_api_error_retorna_erro = _TopLevelFunctionSurface.test_vision_extraction_api_error_retorna_erro
test_vision_extraction_json_invalido_retorna_lista_vazia = _TopLevelFunctionSurface.test_vision_extraction_json_invalido_retorna_lista_vazia
test_vision_extraction_retorna_produtos = _TopLevelFunctionSurface.test_vision_extraction_retorna_produtos
test_vision_extraction_usa_chave_do_usuario = _TopLevelFunctionSurface.test_vision_extraction_usa_chave_do_usuario
test_vision_extraction_descarta_produtos_sem_nome = _TopLevelFunctionSurface.test_vision_extraction_descarta_produtos_sem_nome
