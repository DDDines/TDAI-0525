"""Channel-specific content generation service."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from Backend.infrastructure.adapters.ia_generation_adapter import IAGenerationServiceAdapter
from Backend.infrastructure.repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)

CANAL_PROMPTS = {
    "mercado_livre": {
        "titulo": (
            "Gere um titulo de produto para Mercado Livre com no MAXIMO 60 caracteres. "
            "Comece com a marca (se disponivel), inclua o nome do produto e 1-2 atributos chave. "
            "Use virgulas para separar atributos. Nao use emojis. Retorne apenas o titulo.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}\nDescricao atual: {descricao_atual}"
        ),
        "descricao": (
            "Gere uma descricao de produto para Mercado Livre. Seja clara, objetiva e persuasiva. "
            "Inclua caracteristicas principais, especificacoes tecnicas e beneficios. "
            "Use bullet points com •. Maximo 800 caracteres. Retorne apenas a descricao.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nSKU: {sku}\n"
            "Dados web: {dados_web}\nTitulo gerado: {titulo_gerado}"
        ),
    },
    "google_shopping": {
        "titulo": (
            "Gere um titulo de produto para Google Shopping com no MAXIMO 150 caracteres. "
            "Formato ideal: [Marca] [Nome do Produto] [Atributo 1] [Atributo 2]. "
            "Inclua palavras-chave de busca relevantes. Retorne apenas o titulo.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
        "descricao": (
            "Gere uma descricao de produto para Google Shopping. Foque em atributos tecnicos "
            "e palavras-chave relevantes. Maximo 500 caracteres. Retorne apenas a descricao.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
    },
    "b2b": {
        "titulo": (
            "Gere um titulo tecnico de produto para catalogo B2B/distribuidores. "
            "Inclua nome tecnico, marca, codigo/modelo e especificacoes essenciais. "
            "Maximo 120 caracteres. Retorne apenas o titulo.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
        "descricao": (
            "Gere uma descricao tecnica para catalogo B2B. Foque em especificacoes tecnicas, "
            "compatibilidade, aplicacoes e codigo de referencia. Maximo 600 caracteres. "
            "Retorne apenas a descricao.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
    },
    "ecommerce": {
        "titulo": (
            "Gere um titulo atraente para ecommerce generico. Equilibre SEO com legibilidade: "
            "inclua marca, produto e atributo diferencial. Maximo 100 caracteres. "
            "Retorne apenas o titulo.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
        "descricao": (
            "Gere uma descricao envolvente para ecommerce. Inclua beneficios para o cliente, "
            "caracteristicas principais e especificacoes tecnicas resumidas. Maximo 700 caracteres. "
            "Use paragrafos curtos e retorne apenas a descricao.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nSKU: {sku}\n"
            "Dados web: {dados_web}\nDescricao atual: {descricao_atual}"
        ),
    },
}

CANAL_LABELS = {
    "mercado_livre": "Mercado Livre",
    "google_shopping": "Google Shopping",
    "b2b": "B2B / Distribuidores",
    "ecommerce": "E-commerce",
}

VALID_CANAIS = set(CANAL_PROMPTS.keys())


class ChannelContentService:
    """Generate channel-specific title and description variants for a product."""

    def __init__(
        self,
        *,
        db: Session,
        models: Any,
        product_repository_factory: Any = ProductRepository,
        ia_generation_adapter: Any | None = None,
    ) -> None:
        """Bind the service to its DB session, model module and infrastructure ports."""
        self._db = db
        self._models = models
        self._product_repository = product_repository_factory(db)
        self._ia_generation_adapter = ia_generation_adapter or IAGenerationServiceAdapter()

    def _build_prompt(self, template: str, produto: Any, titulo_gerado: str = "") -> str:
        """Build a prompt string using product base data and enrichment context."""
        dados_web_str = ""
        if produto.dados_brutos_web:
            raw = produto.dados_brutos_web if isinstance(produto.dados_brutos_web, dict) else {}
            parts = []
            if raw.get("descricao_detalhada"):
                parts.append(f"Descricao: {str(raw['descricao_detalhada'])[:400]}")
            if raw.get("especificacoes"):
                parts.append(f"Especificacoes: {str(raw['especificacoes'])[:300]}")
            dados_web_str = " | ".join(parts)

        return template.format(
            nome_base=produto.nome_base or "",
            marca=produto.marca or "",
            modelo=produto.modelo or "",
            sku=produto.sku or "",
            dados_web=dados_web_str or "Sem dados de enriquecimento web",
            descricao_atual=produto.descricao_chat_api or "",
            titulo_gerado=titulo_gerado,
        )

    async def _gerar_texto_simples(self, *, prompt: str, max_tokens: int, user: Any) -> str:
        """Generate freeform text through the IA adapter."""
        return await self._ia_generation_adapter.gerar_texto_livre_com_openai(
            session=self._db,
            user=user,
            prompt=prompt,
            max_tokens=max_tokens,
        )

    async def generate_canal_content(
        self,
        *,
        produto_id: int,
        canal: str,
        user: Any,
        gerar_titulo: bool = True,
        gerar_descricao: bool = True,
    ) -> Dict[str, Any]:
        """Generate and persist channel-specific content for the given product."""
        if canal not in VALID_CANAIS:
            raise ValueError(f"Canal invalido: {canal}. Use: {', '.join(sorted(VALID_CANAIS))}")

        produto = self._product_repository.get_produto(produto_id=produto_id, user_id=user.id)
        if not produto:
            raise ValueError(f"Produto {produto_id} nao encontrado.")

        prompts = CANAL_PROMPTS[canal]
        existing = (produto.conteudo_canais or {}).copy()
        canal_data = existing.get(canal, {})

        titulo: Optional[str] = canal_data.get("titulo")
        descricao: Optional[str] = canal_data.get("descricao")

        if gerar_titulo:
            titulo = await self._gerar_texto_simples(
                prompt=self._build_prompt(prompts["titulo"], produto),
                max_tokens=200,
                user=user,
            )

        if gerar_descricao:
            descricao = await self._gerar_texto_simples(
                prompt=self._build_prompt(
                    prompts["descricao"],
                    produto,
                    titulo_gerado=titulo or "",
                ),
                max_tokens=600,
                user=user,
            )

        canal_data = {
            "titulo": titulo,
            "descricao": descricao,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        }
        all_canais = (produto.conteudo_canais or {}).copy()
        all_canais[canal] = canal_data
        produto.conteudo_canais = all_canais
        flag_modified(produto, "conteudo_canais")
        self._db.commit()
        self._db.refresh(produto)

        return {
            "produto_id": produto_id,
            "canal": canal,
            "titulo": titulo,
            "descricao": descricao,
            "gerado_em": canal_data["gerado_em"],
        }
