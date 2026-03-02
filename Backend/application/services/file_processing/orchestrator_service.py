"""Module orchestrator service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from Backend.application.services.file_processing.contracts import FileProcessingPort
from Backend.application.services.file_processing.pdf_assets_service import (
    FileProcessingPdfAssetsService,
)
from Backend.application.services.file_processing.pdf_ingestion_service import (
    FileProcessingPdfIngestionService,
)
from Backend.application.services.file_processing.preview_service import (
    FileProcessingPreviewService,
)
from Backend.application.services.file_processing.storage_service import (
    FileProcessingStorageService,
)
from Backend.application.services.file_processing.tabular_ingestion_service import (
    FileProcessingTabularIngestionService,
)


class FileProcessingOrchestratorService:
    """Servico OO unificado para processamento de arquivos de catalogo."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port
        self.storage = FileProcessingStorageService(port)
        self.tabular = FileProcessingTabularIngestionService(port)
        self.pdf = FileProcessingPdfIngestionService(port)
        self.preview = FileProcessingPreviewService(port)
        self.pdf_assets = FileProcessingPdfAssetsService(port)

    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ):
        """Execute save_uploaded_catalog.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.storage.save_uploaded_catalog(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Execute delete_catalog_file.

        This callable is documented to make behavior explicit for readers.
        """
        return self.storage.delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str | int) -> str:
        """Execute get_file_path_by_id.

        This callable is documented to make behavior explicit for readers.
        """
        return self.storage.get_file_path_by_id(db=db, file_id=file_id)

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute processar_arquivo_excel.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.tabular.processar_arquivo_excel(
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
        """Execute processar_arquivo_csv.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.tabular.processar_arquivo_csv(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            product_type_id=product_type_id,
        )

    async def processar_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        usar_llm: bool = True,
        product_type_id: Optional[int] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute processar_arquivo_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.pdf.processar_arquivo_pdf(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            usar_llm=usar_llm,
            product_type_id=product_type_id,
            pages=pages,
            region=region,
        )

    async def preview_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute preview_arquivo_excel.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.tabular.preview_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute preview_arquivo_csv.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.tabular.preview_arquivo_csv(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]:
        """Execute preview_arquivo_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.preview.preview_arquivo_pdf(
            conteudo_arquivo=conteudo_arquivo,
            ext=ext,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
        )

    async def gerar_preview(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute gerar_preview.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.preview.gerar_preview(
            conteudo_arquivo=conteudo_arquivo,
            ext=ext,
            max_rows=max_rows,
        )

    async def pdf_bytes_to_images(
        self,
        conteudo_arquivo: bytes,
        max_pages: int = 1,
        start_page: int = 1,
        dpi: int = 200,
    ) -> List[str]:
        """Execute pdf_bytes_to_images.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.preview.pdf_bytes_to_images(
            conteudo_arquivo=conteudo_arquivo,
            max_pages=max_pages,
            start_page=start_page,
            dpi=dpi,
        )

    def pdf_pages_to_images(
        self,
        db: Session,
        file: UploadFile,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Execute pdf_pages_to_images.

        This callable is documented to make behavior explicit for readers.
        """
        return self.preview.pdf_pages_to_images(
            db=db,
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )

    async def extrair_pagina_pdf(
        self,
        conteudo_pdf: bytes,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Execute extrair_pagina_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        return await self.pdf.extrair_pagina_pdf(
            conteudo_pdf=conteudo_pdf,
            page_number=page_number,
            region=region,
        )

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate_pdf_page_images.

        This callable is documented to make behavior explicit for readers.
        """
        return self.pdf_assets.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Execute extract_pdf_region_image.

        This callable is documented to make behavior explicit for readers.
        """
        return self.pdf_assets.extract_pdf_region_image(
            file_path=file_path,
            page_number=page_number,
            region=region,
            dpi=dpi,
        )

    def parse_annotation_to_dataframe(
        self,
        annotation: object,
        vertical_tolerance: int = 5,
    ) -> pd.DataFrame:
        """Execute parse_annotation_to_dataframe.

        This callable is documented to make behavior explicit for readers.
        """
        return self.pdf_assets.parse_annotation_to_dataframe(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )

    def extract_data_from_pdf_region(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """Execute extract_data_from_pdf_region.

        This callable is documented to make behavior explicit for readers.
        """
        return self.pdf.extract_data_from_pdf_region(
            file_path=file_path,
            page_number=page_number,
            region=region,
        )

    async def process_pdf_job(
        self,
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        """Execute process_pdf_job.

        This callable is documented to make behavior explicit for readers.
        """
        await self.pdf.process_pdf_job(
            job_id=job_id,
            pdf_path=pdf_path,
            start_page=start_page,
            mapping=mapping,
        )

    def extract_data_from_single_page(self, file_path: str, page_number: int) -> Dict[str, Any]:
        """Execute extract_data_from_single_page.

        This callable is documented to make behavior explicit for readers.
        """
        return self.pdf.extract_data_from_single_page(file_path=file_path, page_number=page_number)

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """Execute processar_linha_padronizada.

        This callable is documented to make behavior explicit for readers.
        """
        return self.tabular.processar_linha_padronizada(
            linha_original,
            mapeamento_colunas_usuario,
        )
