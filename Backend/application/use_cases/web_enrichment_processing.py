"""Document web enrichment processing module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand

TaskExecutor = Callable[..., Awaitable[Any]]


class WebEnrichmentProcessingUseCase:
    """Caso de uso OO para enriquecimento web.

    Nesta etapa, o caso de uso ainda usa o executor legado injetado,
    mas centraliza validacao e normalizacao antes da execucao.
    """

    def __init__(self, processor: TaskExecutor):
        """Initialize injected dependencies and runtime configuration for Web Enrichment Processing Use Case."""
        self._processor = processor

    async def execute_command(
        self,
        *,
        command: WebEnrichmentStartCommand,
    ) -> Any:
        """Execute execute command as part of this module workflow."""
        produto_id = self._require_positive_int(command.produto_id, "produto_id")
        user_id = self._require_positive_int(command.user_id, "user_id")
        termos_busca_override = self._normalize_search_terms(command.termos_busca_override)
        usar_ia = self._normalize_use_ai(command.usar_ia)

        processor_kwargs = {
            "produto_id": produto_id,
            "user_id": user_id,
            "termos_busca_override": termos_busca_override,
        }
        if usar_ia is not None:
            processor_kwargs["usar_ia"] = usar_ia

        return await self._processor(**processor_kwargs)

    async def execute(
        self,
        *,
        produto_id: Any,
        user_id: Any,
        termos_busca_override: Any = None,
        usar_ia: Any = None,
    ) -> Any:
        """Execute execute as part of this module workflow."""
        command = WebEnrichmentStartCommand(
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
            usar_ia=usar_ia,
        )
        return await self.execute_command(
            command=command,
        )

    @staticmethod
    def _require_positive_int(raw_value: Any, field_name: str) -> int:
        """Execute require positive int as part of this module workflow."""
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} deve ser inteiro positivo") from None
        if value <= 0:
            raise ValueError(f"{field_name} deve ser inteiro positivo")
        return value

    @staticmethod
    def _normalize_search_terms(raw_terms: Any) -> Optional[str]:
        """Normalize search terms to keep behavior consistent across callers."""
        if raw_terms is None:
            return None
        text = str(raw_terms).strip()
        if not text:
            return None
        # Guarda para evitar payload enorme ou termos inviaveis.
        return text[:500]

    @staticmethod
    def _normalize_use_ai(raw_value: Any) -> Optional[bool]:
        """Normalize explicit AI opt-in so UI and background callers behave consistently."""
        if raw_value is None:
            return None
        if isinstance(raw_value, bool):
            return raw_value
        text = str(raw_value).strip().lower()
        if text in {"1", "true", "sim", "yes", "on"}:
            return True
        if text in {"0", "false", "nao", "não", "no", "off"}:
            return False
        return bool(raw_value)
