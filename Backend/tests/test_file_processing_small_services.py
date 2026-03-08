"""Coverage for small file-processing service wrappers."""

from __future__ import annotations

import pytest

from Backend.application.services.file_processing.pdf_assets_service import (
    FileProcessingPdfAssetsService,
)
from Backend.application.services.file_processing.tabular_ingestion_service import (
    FileProcessingTabularIngestionService,
)


class _PortStub:
    """Capture calls delegated by small file-processing services."""

    def __init__(self):
        self.calls = []

    def generate_pdf_page_images(self, **kwargs):
        self.calls.append(("generate_pdf_page_images", kwargs))
        return ["img-1"]

    def extract_pdf_region_image(self, **kwargs):
        self.calls.append(("extract_pdf_region_image", kwargs))
        return b"png"

    def parse_annotation_to_dataframe(self, **kwargs):
        self.calls.append(("parse_annotation_to_dataframe", kwargs))
        return {"rows": 1}

    async def processar_arquivo_excel(self, **kwargs):
        self.calls.append(("processar_arquivo_excel", kwargs))
        return [{"nome_base": "excel"}]

    async def processar_arquivo_csv(self, **kwargs):
        self.calls.append(("processar_arquivo_csv", kwargs))
        return [{"nome_base": "csv"}]

    async def preview_arquivo_excel(self, **kwargs):
        self.calls.append(("preview_arquivo_excel", kwargs))
        return {"headers": ["A"]}

    async def preview_arquivo_csv(self, **kwargs):
        self.calls.append(("preview_arquivo_csv", kwargs))
        return {"headers": ["B"]}

    def processar_linha_padronizada(self, **kwargs):
        self.calls.append(("processar_linha_padronizada", kwargs))
        return {"nome_base": "linha"}


class _TopLevelFunctionSurface:
    """Represent top level function surface and centralize responsibilities for this module."""

    def test_pdf_assets_service_delegates_all_methods():
        """Cover all PDF asset wrapper entrypoints."""
        port = _PortStub()
        service = FileProcessingPdfAssetsService(port)

        assert service.generate_pdf_page_images("c:/x.pdf", "10") == ["img-1"]
        assert service.extract_pdf_region_image("c:/x.pdf", 2, [1, 2, 3, 4], 200) == b"png"
        assert service.parse_annotation_to_dataframe({"x": 1}, vertical_tolerance=9) == {"rows": 1}
        assert [call[0] for call in port.calls] == [
            "generate_pdf_page_images",
            "extract_pdf_region_image",
            "parse_annotation_to_dataframe",
        ]

    @pytest.mark.asyncio
    async def test_tabular_ingestion_service_delegates_all_methods():
        """Cover all tabular ingestion wrapper entrypoints."""
        port = _PortStub()
        service = FileProcessingTabularIngestionService(port)

        assert await service.processar_arquivo_excel(b"x", {"A": "nome"}, "Plan1", 7) == [{"nome_base": "excel"}]
        assert await service.processar_arquivo_csv(b"y", {"B": "nome"}, 8) == [{"nome_base": "csv"}]
        assert await service.preview_arquivo_excel(b"z", max_rows=7) == {"headers": ["A"]}
        assert await service.preview_arquivo_csv(b"w", max_rows=4) == {"headers": ["B"]}
        assert service.processar_linha_padronizada({"A": "1"}, {"A": "nome"}) == {"nome_base": "linha"}
        assert [call[0] for call in port.calls] == [
            "processar_arquivo_excel",
            "processar_arquivo_csv",
            "preview_arquivo_excel",
            "preview_arquivo_csv",
            "processar_linha_padronizada",
        ]


test_pdf_assets_service_delegates_all_methods = _TopLevelFunctionSurface.test_pdf_assets_service_delegates_all_methods
test_tabular_ingestion_service_delegates_all_methods = (
    _TopLevelFunctionSurface.test_tabular_ingestion_service_delegates_all_methods
)
