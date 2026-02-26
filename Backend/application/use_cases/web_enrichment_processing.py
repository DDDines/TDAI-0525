from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

TaskExecutor = Callable[..., Awaitable[Any]]


class WebEnrichmentProcessingUseCase:
    """Caso de uso OO para enriquecimento web.

    Nesta etapa, o caso de uso ainda usa o executor legado injetado,
    mas centraliza validacao e normalizacao antes da execucao.
    """

    def __init__(self, processor: TaskExecutor):
        self._processor = processor

    async def execute(self, **task_kwargs: Any) -> Any:
        produto_id = self._require_positive_int(task_kwargs.get("produto_id"), "produto_id")
        user_id = self._require_positive_int(task_kwargs.get("user_id"), "user_id")
        termos_busca_override = self._normalize_search_terms(
            task_kwargs.get("termos_busca_override")
        )

        return await self._processor(
            db_session_factory=task_kwargs.get("db_session_factory"),
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

    @staticmethod
    def _require_positive_int(raw_value: Any, field_name: str) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} deve ser inteiro positivo") from None
        if value <= 0:
            raise ValueError(f"{field_name} deve ser inteiro positivo")
        return value

    @staticmethod
    def _normalize_search_terms(raw_terms: Any) -> Optional[str]:
        if raw_terms is None:
            return None
        text = str(raw_terms).strip()
        if not text:
            return None
        # Guarda para evitar payload enorme ou termos inviaveis.
        return text[:500]
