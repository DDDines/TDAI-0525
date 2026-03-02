"""Module test file processing pdf asset workflow.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_pdf_asset_workflow_usa_runtime_de_conversao():
        """Execute test_pdf_asset_workflow_usa_runtime_de_conversao.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        class FakeImageRuntime:
            """Class FakeImageRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def pdf_bytes_to_images(self, **kwargs):
                """Execute pdf_bytes_to_images.

                This callable is documented to make behavior explicit for readers.
                """
                called.update(kwargs)
                return ["img64"]
    
        class FakeAssetRuntime:
            """Class FakeAssetRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def generate_pdf_page_images(self, **kwargs):
                """Execute generate_pdf_page_images.

                This callable is documented to make behavior explicit for readers.
                """
                return []
    
            def extract_pdf_region_image(self, **kwargs):
                """Execute extract_pdf_region_image.

                This callable is documented to make behavior explicit for readers.
                """
                return b""
    
            def parse_annotation_to_dataframe(self, **kwargs):
                """Execute parse_annotation_to_dataframe.

                This callable is documented to make behavior explicit for readers.
                """
                return pd.DataFrame()
    
        workflow = file_processing.PdfAssetWorkflow(
            pdf_image_runtime=FakeImageRuntime(),
            pdf_asset_runtime=FakeAssetRuntime(),
        )
    
        result = await workflow.pdf_bytes_to_images(
            conteudo_arquivo=b"pdf",
            max_pages=2,
            start_page=3,
            dpi=150,
        )
    
        assert result == ["img64"]
        assert called["conteudo_arquivo"] == b"pdf"
        assert called["max_pages"] == 2
        assert called["start_page"] == 3
        assert called["dpi"] == 150

    def test_pdf_asset_workflow_usa_runtime_de_assets():
        """Execute test_pdf_asset_workflow_usa_runtime_de_assets.

        This callable is documented to make behavior explicit for readers.
        """
        called = {"generate": {}, "extract": {}, "parse": {}}
        expected_df = pd.DataFrame([{"col_1": "ok"}])
    
        class FakeImageRuntime:
            """Class FakeImageRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def pdf_bytes_to_images(self, **kwargs):
                """Execute pdf_bytes_to_images.

                This callable is documented to make behavior explicit for readers.
                """
                _ = kwargs
                return []
    
        class FakeAssetRuntime:
            """Class FakeAssetRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def generate_pdf_page_images(self, **kwargs):
                """Execute generate_pdf_page_images.

                This callable is documented to make behavior explicit for readers.
                """
                called["generate"].update(kwargs)
                return ["/static/previews/x/page-1.png"]
    
            def extract_pdf_region_image(self, **kwargs):
                """Execute extract_pdf_region_image.

                This callable is documented to make behavior explicit for readers.
                """
                called["extract"].update(kwargs)
                return b"img"
    
            def parse_annotation_to_dataframe(self, **kwargs):
                """Execute parse_annotation_to_dataframe.

                This callable is documented to make behavior explicit for readers.
                """
                called["parse"].update(kwargs)
                return expected_df
    
        workflow = file_processing.PdfAssetWorkflow(
            pdf_image_runtime=FakeImageRuntime(),
            pdf_asset_runtime=FakeAssetRuntime(),
        )
    
        gen = workflow.generate_pdf_page_images("C:/tmp/a.pdf", "x")
        extract = workflow.extract_pdf_region_image(
            file_path="C:/tmp/a.pdf",
            page_number=5,
            region=[1.0, 2.0, 3.0, 4.0],
            dpi=240,
        )
        parsed = workflow.parse_annotation_to_dataframe(annotation=object(), vertical_tolerance=11)
    
        assert gen == ["/static/previews/x/page-1.png"]
        assert extract == b"img"
        assert parsed.equals(expected_df)
        assert called["generate"] == {"file_path": "C:/tmp/a.pdf", "file_id": "x"}
        assert called["extract"] == {
            "file_path": "C:/tmp/a.pdf",
            "page_number": 5,
            "region": [1.0, 2.0, 3.0, 4.0],
            "dpi": 240,
        }
        assert called["parse"]["vertical_tolerance"] == 11

test_pdf_asset_workflow_usa_runtime_de_conversao = _TopLevelFunctionSurface.test_pdf_asset_workflow_usa_runtime_de_conversao
test_pdf_asset_workflow_usa_runtime_de_assets = _TopLevelFunctionSurface.test_pdf_asset_workflow_usa_runtime_de_assets




