"""Application service for effective AI policy resolution and enforcement."""

from __future__ import annotations

from fastapi import HTTPException, status

from Backend import models
from Backend.infrastructure.repositories.ai_policy_repository import AIPolicyRepository


class AIPolicyService:
    """Resolve effective AI policy and enforce the current transport-layer permissions."""

    def __init__(self, repository: AIPolicyRepository) -> None:
        """Bind the service to the current repository instance."""
        self._repository = repository

    def get_effective_policy(self, *, current_user: models.User):
        """Return the resolved effective policy for the authenticated user."""
        return self._repository.resolve_effective_config(current_user=current_user)

    def ensure_generation_provider_allowed(
        self,
        *,
        current_user: models.User,
        provider: models.ExternalCredentialProviderEnum,
    ) -> dict:
        """Block AI generation endpoints when current policy does not allow them."""
        effective_policy = self.get_effective_policy(current_user=current_user)
        if effective_policy["generation_default_mode"] != models.AIPolicyModeEnum.COMPLETE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A politica atual permite apenas geracao basica.",
            )
        if provider == models.ExternalCredentialProviderEnum.OPENAI and not effective_policy["allow_openai"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A politica atual nao permite geracao via OpenAI.",
            )
        if provider == models.ExternalCredentialProviderEnum.GOOGLE_GEMINI and not effective_policy["allow_gemini"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A politica atual nao permite geracao via Gemini.",
            )
        return effective_policy

    def ensure_attribute_ai_allowed(self, *, current_user: models.User) -> dict:
        """Block attribute suggestion endpoints when policy disallows AI assistance."""
        effective_policy = self.get_effective_policy(current_user=current_user)
        if effective_policy["generation_default_mode"] != models.AIPolicyModeEnum.COMPLETE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A politica atual permite apenas o modo basico.",
            )
        if not effective_policy["allow_attribute_ai"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A politica atual nao permite sugestoes de atributos com IA.",
            )
        return effective_policy

    def ensure_web_enrichment_allowed(
        self,
        *,
        current_user: models.User,
        usar_ia: bool | None,
    ) -> dict:
        """Block LLM-backed enrichment when policy disallows the AI step."""
        effective_policy = self.get_effective_policy(current_user=current_user)
        if usar_ia:
            if effective_policy["enrichment_default_mode"] != models.AIPolicyModeEnum.COMPLETE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="A politica atual permite apenas enriquecimento basico.",
                )
            if not effective_policy["allow_web_llm"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="A politica atual nao permite enriquecimento com IA.",
                )
        return effective_policy
