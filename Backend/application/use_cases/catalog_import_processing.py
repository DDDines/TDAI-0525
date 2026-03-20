"""Document catalog import processing module responsibilities and runtime integration points."""

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
        """Initialize injected dependencies and runtime configuration for Catalog Import Processing Use Case."""
        self._processor = processor

    async def execute_command(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> Any:
        """Execute execute command as part of this module workflow."""
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
        extraction_mode = self._normalize_extraction_mode(command.extraction_mode)

        return await self._processor(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            extraction_mode=extraction_mode,
        )

    async def execute(
        self,
        *,
        file_id: Any,
        user_id: Any,
        product_type_id: Any,
        fornecedor_id: Any,
        mapping: Any = None,
        pages: Any = None,
        region: Any = None,
        extraction_mode: Any = "ocr",
    ) -> Any:
        """Execute execute as part of this module workflow."""
        command = CatalogImportFinalizeCommand(
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            extraction_mode=extraction_mode,
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

    @classmethod
    def _normalize_mapping(cls, raw_mapping: Any) -> Optional[Dict[str, str]]:
        """Normalize mapping to keep behavior consistent across callers."""
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
        """Normalize pages to keep behavior consistent across callers."""
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
        """Normalize region to keep behavior consistent across callers."""
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

    @staticmethod
    def _normalize_extraction_mode(raw_mode: Any) -> str:
        """Normalize extraction mode to keep behavior consistent across callers."""
        if raw_mode is None:
            return "ocr"
        normalized = str(raw_mode).strip().lower()
        if not normalized:
            return "ocr"
        if normalized not in {"table", "ocr", "ia", "vision"}:
            raise ValueError("extraction_mode deve ser um de: table, ocr, ia, vision")
        return normalized
