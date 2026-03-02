"""Module fornecedor preview service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import uuid

import pdfplumber
from fastapi import HTTPException


class FornecedorPreviewService:
    """Centraliza preview e extracao de dados de catalogo PDF para fornecedores."""

    def __init__(
        self,
        *,
        file_processing_service: Any,
        web_data_extractor_service: Any,
        catalog_file_repository: Any,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._file_processing_service = file_processing_service
        self._web_data_extractor_service = web_data_extractor_service
        self._catalog_file_repository = catalog_file_repository

    def _resolve_session(self) -> Any:
        """Execute _resolve_session.

        This callable is documented to make behavior explicit for readers.
        """
        return getattr(self._catalog_file_repository, "_db", None)

    async def preview_pages(self, *, file: Any) -> dict[str, Any]:
        """Execute preview_pages.

        This callable is documented to make behavior explicit for readers.
        """
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF sao permitidos.")

        file_id = uuid.uuid4().hex
        tmp_dir = Path(os.getenv("TMPDIR", "/tmp"))
        tmp_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = tmp_dir / f"{file_id}.pdf"

        contents = await file.read()
        with open(pdf_path, "wb") as out_file:
            out_file.write(contents)

        page_image_urls = self._file_processing_service.generate_pdf_page_images(
            str(pdf_path), file_id
        )
        return {"file_id": file_id, "page_image_urls": page_image_urls}

    def preview_pdf(
        self,
        *,
        file: Any,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> Any:
        """Execute preview_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        session = self._resolve_session()
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Tipo de ficheiro invalido. Apenas PDFs sao permitidos.",
            )

        return self._file_processing_service.pdf_pages_to_images(
            db=session,
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )

    def preview_catalog_from_region(
        self,
        *,
        file_id: int,
        page_number: int,
        region: list[float],
    ) -> dict[str, Any]:
        """Execute preview_catalog_from_region.

        This callable is documented to make behavior explicit for readers.
        """
        session = self._resolve_session()
        file_path = self._file_processing_service.get_file_path_by_id(
            session,
            file_id=file_id,
        )
        if not file_path:
            raise HTTPException(status_code=404, detail="Arquivo de catalogo nao encontrado")

        image_bytes = self._file_processing_service.extract_pdf_region_image(
            file_path=file_path,
            page_number=page_number,
            region=region,
        )
        annotation = self._web_data_extractor_service.extract_text_from_image_region(
            image_bytes
        )
        df = self._file_processing_service.parse_annotation_to_dataframe(annotation)

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Nao foi possivel extrair dados da regiao selecionada. "
                    "Tente selecionar uma area diferente ou ajustar as configuracoes."
                ),
            )

        return {
            "columns": df.columns.astype(str).tolist(),
            "data": df.head(10).to_dict(orient="records"),
        }

    def extract_data_from_pdf_bulk(
        self,
        *,
        background_tasks: Any,
        file_id: int,
        region: list[float],
        pages: list[int] | None,
        all_pages: bool,
    ) -> dict[str, Any]:
        """Execute extract_data_from_pdf_bulk.

        This callable is documented to make behavior explicit for readers.
        """
        session = self._resolve_session()
        file_path = self._file_processing_service.get_file_path_by_id(
            session,
            file_id=file_id,
        )
        if not file_path:
            raise HTTPException(status_code=404, detail="Arquivo de catalogo nao encontrado")

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

        target_pages = pages or []
        if all_pages or not target_pages:
            target_pages = list(range(1, total_pages + 1))

        for page_number in target_pages:
            if 1 <= page_number <= total_pages:
                background_tasks.add_task(
                    self._file_processing_service.extract_data_from_pdf_region,
                    file_path=file_path,
                    page_number=page_number,
                    region=region,
                )

        return {"detail": "Batch processing started", "total_pages": total_pages}
