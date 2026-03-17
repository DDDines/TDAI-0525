"""Vision extraction module using GPT-4o Vision for high-fidelity PDF catalog import."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_VISION_PROMPT = """Voce e um especialista em extracao de dados de catalogos de produtos.
Analise a imagem da pagina do catalogo e extraia cada produto visivel.

Para cada produto encontrado, retorne um objeto JSON com os campos abaixo.
Use null quando o campo nao estiver visivel na imagem.

{
  "produtos": [
    {
      "nome_base": "<nome principal do produto>",
      "sku_original": "<codigo SKU ou referencia>",
      "ean_original": "<codigo EAN/barras de 13 digitos>",
      "descricao_original": "<descricao completa>",
      "marca": "<marca ou fabricante>",
      "categoria_original": "<categoria>",
      "preco_original": "<preco como string, ex: R$ 49,90>",
      "imagem_url_original": "<URL da imagem se visivel>"
    }
  ]
}

Regras:
- Extraia cada produto da pagina, mesmo os incompletos
- Preserve o texto exato sem interpretar ou inventar dados
- Se a pagina nao contiver produtos, retorne {"produtos": []}
- Retorne apenas JSON valido, sem texto adicional"""


class VisionExtractionRuntime:
    """Runtime OO para extracao de produtos com GPT-4o Vision."""

    MODEL = "gpt-4o"

    def __init__(self, settings: Any = None) -> None:
        """Initialize injected dependencies and runtime configuration for Vision Extraction Runtime."""
        self._settings = settings

    def _resolve_api_key(self, *, user: Optional[Any]) -> Optional[str]:
        """Resolve OpenAI API key from user personal key or system settings."""
        if user is not None:
            personal_key = str(getattr(user, "chave_openai_pessoal", "") or "").strip()
            if personal_key:
                return personal_key
        if self._settings is not None:
            system_key = str(getattr(self._settings, "OPENAI_API_KEY", "") or "").strip()
            if system_key:
                return system_key
        from Backend.core.config import settings as default_settings
        return str(getattr(default_settings, "OPENAI_API_KEY", "") or "").strip() or None

    def _build_vision_message(
        self,
        page_image_data_url: str,
        page_text: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Build multimodal message content for GPT-4o Vision."""
        content: List[Dict[str, Any]] = []
        if page_text and page_text.strip():
            content.append({
                "type": "text",
                "text": f"Texto extraido da pagina (pode estar incompleto):\n{page_text.strip()[:3000]}\n\n{_VISION_PROMPT}",
            })
        else:
            content.append({"type": "text", "text": _VISION_PROMPT})
        content.append({
            "type": "image_url",
            "image_url": {
                "url": page_image_data_url,
                "detail": "high",
            },
        })
        return content

    async def extrair_pagina_com_gpt4_vision(
        self,
        *,
        page_image_data_url: str,
        page_text: Optional[str] = None,
        user: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Extract all products from a single PDF page image using GPT-4o Vision.

        Returns a list of product dicts in the same format as other extractors.
        Returns an empty list if no products are found or if the API call fails.
        """
        api_key = self._resolve_api_key(user=user)
        if not api_key:
            logger.warning(
                "vision_extraction: nenhuma chave OpenAI configurada; modo vision indisponivel."
            )
            return [{"erro_processamento_pdf": "Chave OpenAI nao configurada para modo Vision. Configure em Credenciais ou variavel OPENAI_API_KEY."}]

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.error("vision_extraction: openai nao instalado.")
            return [{"erro_processamento_pdf": "Biblioteca openai nao instalada."}]

        client = AsyncOpenAI(api_key=api_key)
        messages = [
            {
                "role": "user",
                "content": self._build_vision_message(
                    page_image_data_url=page_image_data_url,
                    page_text=page_text,
                ),
            }
        ]

        try:
            response = await client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                max_tokens=2000,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_content = response.choices[0].message.content or "{}"
        except Exception as api_err:
            logger.warning("vision_extraction: erro na API OpenAI: %s", api_err)
            return [{"erro_processamento_pdf": f"Erro na API Vision: {str(api_err)[:200]}"}]

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            logger.warning("vision_extraction: resposta nao e JSON valido.")
            return []

        produtos_raw = parsed.get("produtos") or []
        if not isinstance(produtos_raw, list):
            return []

        results: List[Dict[str, Any]] = []
        for item in produtos_raw:
            if not isinstance(item, dict):
                continue
            nome = (item.get("nome_base") or "").strip()
            if not nome:
                continue
            results.append(item)

        logger.info("vision_extraction: %s produto(s) extraidos da pagina.", len(results))
        return results
