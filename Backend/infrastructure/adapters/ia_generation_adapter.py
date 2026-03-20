"""Document ia generation adapter module responsibilities and runtime integration points."""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.infrastructure.runtime_modules.ia_generation_module import (
    IAGenerationWorkflow,
)


class IAGenerationServiceAdapter:
    """OOP port adapter backed by the current IA generation implementation."""

    def __init__(self, runtime: IAGenerationWorkflow | None = None) -> None:
        """Initialize injected dependencies and runtime configuration for IAGeneration Service Adapter."""
        self._runtime = runtime or IAGenerationWorkflow()

    async def gerar_titulos_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]:
        """Execute gerar titulos com openai as part of this module workflow."""
        return await self._runtime.gerar_titulos_com_openai(
            db=session,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        """Execute gerar descricao com openai as part of this module workflow."""
        return await self._runtime.gerar_descricao_com_openai(
            db=session,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def gerar_titulos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]:
        """Execute gerar titulos com gemini as part of this module workflow."""
        return await self._runtime.gerar_titulos_com_gemini(
            db=session,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        """Execute gerar descricao com gemini as part of this module workflow."""
        return await self._runtime.gerar_descricao_com_gemini(
            db=session,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def sugerir_valores_atributos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        """Sugerir valores atributos com gemini."""
        return await self._runtime.sugerir_valores_atributos_com_gemini(
            db=session,
            produto_id=produto_id,
            user=user,
        )

    async def gerar_texto_livre_com_openai(
        self,
        *,
        session: Session,
        user: models.User,
        prompt: str,
        max_tokens: int,
    ) -> str:
        """Generate freeform text with OpenAI using the user's configured credentials."""
        provider_workflow = self._runtime.ai_provider_workflow
        api_key = await provider_workflow.get_openai_api_key(db=session, user=user)
        if not api_key:
            raise ValueError(
                "Chave da API OpenAI nao configurada. "
                "Configure sua chave pessoal ou a chave da empresa para usar a geracao por canal."
            )
        result = await provider_workflow.call_openai_api(
            prompt_messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            max_tokens=max_tokens,
        )
        return result.strip()
