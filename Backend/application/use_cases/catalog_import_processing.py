from __future__ import annotations

from typing import Any, Awaitable, Callable

TaskExecutor = Callable[..., Awaitable[Any]]


class CatalogImportProcessingUseCase:
    """Caso de uso OO para processamento de importação de catálogo.

    Etapa atual da migração: delega para o executor legado injetado.
    A lógica será movida para este caso de uso em passos seguintes.
    """

    def __init__(self, processor: TaskExecutor):
        self._processor = processor

    async def execute(self, **task_kwargs: Any) -> Any:
        return await self._processor(**task_kwargs)
