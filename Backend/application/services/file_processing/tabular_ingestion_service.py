"""Tabular ingestion service.

"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingTabularIngestionService:
    """Ingestao de arquivos tabulares (Excel/CSV)."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Initialize dependencies for FileProcessingTabularIngestionService."""
        self._port = port

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Processar arquivo excel."""
        return await self._port.processar_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            sheet_name=sheet_name,
            product_type_id=product_type_id,
        )

    async def processar_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Processar arquivo csv."""
        return await self._port.processar_arquivo_csv(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            product_type_id=product_type_id,
        )

    async def preview_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Preview arquivo excel."""
        return await self._port.preview_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Preview arquivo csv."""
        return await self._port.preview_arquivo_csv(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Processar linha padronizada."""
        return self._port.processar_linha_padronizada(
            linha_original=linha_original,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        )
