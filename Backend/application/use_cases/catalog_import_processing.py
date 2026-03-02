"""Module catalog import processing.

Contains backend logic related to catalog import processing and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand

TaskExecutor = Callable[..., Awaitable[Any]]


class CatalogImportProcessingUseCase:
    """Caso de uso OO para processamento de importacao de catalogo.

    Nesta etapa, o caso de uso ainda usa o executor legado injetado,
    mas centraliza validacao e normalizacao do comando antes da execucao.
    """

    def __init__(self, processor: TaskExecutor):
        """Initialize collaborators and configuration required by this component."""
        self._processor = processor

    async def execute_command(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> Any:
        """Run execute command in this workflow."""
        file_id = self._require_positive_int(command.file_id, "file_id")
        user_id = self._require_positive_int(command.user_id, "user_id")
        fornecedor_id = self._require_positive_int(command.fornecedor_id, "fornecedor_id")

        product_type_id = None
        if command.product_type_id is not None:
            product_type_id = self._require_positive_int(
                command.product_type_id, "product_type_id"
            )

        mapping = self._normalize_mapping(command.mapping)
        pages = self._normalize_pages(command.pages)
        region = self._normalize_region(command.region)

        return await self._processor(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )

    async def execute(self, **task_kwargs: Any) -> Any:
        """Run execute in this workflow."""
        command = CatalogImportFinalizeCommand(
            file_id=task_kwargs.get("file_id"),
            user_id=task_kwargs.get("user_id"),
            product_type_id=task_kwargs.get("product_type_id"),
            fornecedor_id=task_kwargs.get("fornecedor_id"),
            mapping=task_kwargs.get("mapping"),
            pages=task_kwargs.get("pages"),
            region=task_kwargs.get("region"),
        )
        return await self.execute_command(
            command=command,
        )

    @staticmethod
    def _require_positive_int(raw_value: Any, field_name: str) -> int:
        """Run require positive int in this workflow."""
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValueError(f"{field_name} deve ser inteiro positivo") from None
        if value <= 0:
            raise ValueError(f"{field_name} deve ser inteiro positivo")
        return value

    @classmethod
    def _normalize_mapping(cls, raw_mapping: Any) -> Optional[Dict[str, str]]:
        """Run normalize mapping in this workflow."""
        if raw_mapping is None:
            return None
        if not isinstance(raw_mapping, dict):
            raise ValueError("mapping deve ser um objeto chave/valor")

        normalized: Dict[str, str] = {}
        for raw_key, raw_value in raw_mapping.items():
            key = str(raw_key or "").strip()
            value = str(raw_value or "").strip()
            if not key or not value:
                continue
            normalized[key] = value

        return normalized or None

    @classmethod
    def _normalize_pages(cls, raw_pages: Any) -> Optional[List[int]]:
        """Run normalize pages in this workflow."""
        if raw_pages is None:
            return None
        if not isinstance(raw_pages, list):
            raise ValueError("pages deve ser uma lista de inteiros positivos")

        normalized: List[int] = []
        seen = set()
        for raw_page in raw_pages:
            page = cls._require_positive_int(raw_page, "pages")
            if page in seen:
                continue
            seen.add(page)
            normalized.append(page)
        return normalized or None

    @staticmethod
    def _normalize_region(raw_region: Any) -> Optional[List[float]]:
        """Run normalize region in this workflow."""
        if raw_region is None:
            return None
        if not isinstance(raw_region, list):
            raise ValueError("region deve ser uma lista de 4 numeros")
        if len(raw_region) != 4:
            raise ValueError("region deve ter exatamente 4 coordenadas")

        normalized: List[float] = []
        for value in raw_region:
            try:
                normalized.append(float(value))
            except (TypeError, ValueError):
                raise ValueError("region deve conter apenas numeros") from None
        return normalized
