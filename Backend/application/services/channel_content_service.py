"""Channel-specific content generation service."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CANAL_PROMPTS = {
    "mercado_livre": {
        "titulo": (
            "Gere um título de produto para Mercado Livre com no MÁXIMO 60 caracteres. "
            "Comece com a marca (se disponível), inclua o nome do produto e 1-2 atributos chave. "
            "Use vírgulas para separar atributos. NÃO use emojis. Retorne APENAS o título, sem aspas.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}\nDescrição atual: {descricao_atual}"
        ),
        "descricao": (
            "Gere uma descrição de produto para Mercado Livre. Deve ser clara, objetiva e persuasiva. "
            "Inclua: características principais, especificações técnicas (se disponível), benefícios. "
            "Use bullet points com • . Máximo 800 caracteres. Retorne APENAS a descrição.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nSKU: {sku}\n"
            "Dados web: {dados_web}\nTítulo gerado: {titulo_gerado}"
        ),
    },
    "google_shopping": {
        "titulo": (
            "Gere um título de produto para Google Shopping com no MÁXIMO 150 caracteres. "
            "Formato ideal: [Marca] [Nome do Produto] [Atributo 1] [Atributo 2]. "
            "Inclua palavras-chave de busca relevantes. NÃO use maiúsculas em tudo. Retorne APENAS o título.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
        "descricao": (
            "Gere uma descrição de produto para Google Shopping. Foque em atributos técnicos e palavras-chave "
            "que os compradores pesquisam. Seja direto e informativo. Máximo 500 caracteres. "
            "Retorne APENAS a descrição, sem formatação especial.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
    },
    "b2b": {
        "titulo": (
            "Gere um título técnico de produto para catálogo B2B/distribuidores. "
            "Inclua: nome técnico, marca, código/modelo, especificações essenciais. "
            "Seja preciso e profissional. Máximo 120 caracteres. Retorne APENAS o título.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
        "descricao": (
            "Gere uma descrição técnica para catálogo B2B. Foque em: especificações técnicas, "
            "compatibilidade, aplicações, código de referência. Linguagem profissional e técnica. "
            "Máximo 600 caracteres. Retorne APENAS a descrição.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
    },
    "ecommerce": {
        "titulo": (
            "Gere um título atraente para e-commerce genérico. "
            "Equilibre SEO com legibilidade: inclua marca, produto, atributo diferencial. "
            "Máximo 100 caracteres. Retorne APENAS o título.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nModelo: {modelo}\nSKU: {sku}\n"
            "Dados web: {dados_web}"
        ),
        "descricao": (
            "Gere uma descrição envolvente para e-commerce. Inclua: benefícios para o cliente, "
            "características principais, especificações técnicas resumidas, CTA sutil. "
            "Máximo 700 caracteres. Use parágrafos curtos. Retorne APENAS a descrição.\n\n"
            "Produto: {nome_base}\nMarca: {marca}\nSKU: {sku}\n"
            "Dados web: {dados_web}\nDescrição atual: {descricao_atual}"
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
    """Generates channel-specific title and description for a product."""

    def __init__(self, *, db: Session, models: Any) -> None:
        """Initialize channel content service with a DB session and models module."""
        self._db = db
        self._models = models

    def _build_prompt(self, template: str, produto: Any, titulo_gerado: str = "") -> str:
        """Build a formatted prompt string from the template and product data."""
        dados_web_str = ""
        if produto.dados_brutos_web:
            raw = produto.dados_brutos_web if isinstance(produto.dados_brutos_web, dict) else {}
            parts = []
            if raw.get("descricao_detalhada"):
                parts.append(f"Descrição: {str(raw['descricao_detalhada'])[:400]}")
            if raw.get("especificacoes"):
                parts.append(f"Especificações: {str(raw['especificacoes'])[:300]}")
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
        """Call OpenAI to generate a simple text completion for the given prompt."""
        from Backend.infrastructure.runtime_modules.ia_generation_module import AiProviderWorkflow

        workflow = AiProviderWorkflow()
        api_key = await workflow.get_openai_api_key(db=self._db, user=user)
        if not api_key:
            raise ValueError(
                "Chave da API OpenAI não configurada. "
                "Configure sua chave pessoal ou a chave da empresa para usar a geração por canal."
            )
        messages = [{"role": "user", "content": prompt}]
        result = await workflow.call_openai_api(
            prompt_messages=messages,
            api_key=api_key,
            max_tokens=max_tokens,
        )
        return result.strip()

    async def generate_canal_content(
        self,
        *,
        produto_id: int,
        canal: str,
        user: Any,
        gerar_titulo: bool = True,
        gerar_descricao: bool = True,
    ) -> Dict[str, Any]:
        """Generate channel-specific content for a product."""
        if canal not in VALID_CANAIS:
            raise ValueError(f"Canal inválido: {canal}. Use: {', '.join(sorted(VALID_CANAIS))}")

        produto = (
            self._db.query(self._models.Produto)
            .filter(
                self._models.Produto.id == produto_id,
                self._models.Produto.user_id == user.id,
                self._models.Produto.deleted_at.is_(None),
            )
            .first()
        )

        if not produto:
            raise ValueError(f"Produto {produto_id} não encontrado.")

        prompts = CANAL_PROMPTS[canal]
        existing = (produto.conteudo_canais or {}).copy()
        canal_data = existing.get(canal, {})

        titulo: Optional[str] = canal_data.get("titulo")
        descricao: Optional[str] = canal_data.get("descricao")

        if gerar_titulo:
            prompt_titulo = self._build_prompt(prompts["titulo"], produto)
            titulo = await self._gerar_texto_simples(
                prompt=prompt_titulo,
                max_tokens=200,
                user=user,
            )

        if gerar_descricao:
            prompt_desc = self._build_prompt(
                prompts["descricao"],
                produto,
                titulo_gerado=titulo or "",
            )
            descricao = await self._gerar_texto_simples(
                prompt=prompt_desc,
                max_tokens=600,
                user=user,
            )

        canal_data = {
            "titulo": titulo,
            "descricao": descricao,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        }

        # Merge into conteudo_canais JSON
        all_canais = (produto.conteudo_canais or {}).copy()
        all_canais[canal] = canal_data

        # SQLAlchemy needs assignment to detect JSON mutation
        produto.conteudo_canais = all_canais
        from sqlalchemy.orm.attributes import flag_modified
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
