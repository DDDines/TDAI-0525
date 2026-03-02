"""Module test file processing pdf asset workflow.

Contains backend logic related to test file processing pdf asset workflow and documents its role in the OOP architecture.
"""

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_pdf_asset_workflow_usa_runtime_de_conversao():
        """Run test pdf asset workflow usa runtime de conversao in this workflow."""
        called = {}
    
        class FakeImageRuntime:
            """Represent fake image runtime and centralize responsibilities for this module."""
            async def pdf_bytes_to_images(self, **kwargs):
                """Run pdf bytes to images in this workflow."""
                called.update(kwargs)
                return ["img64"]
    
        class FakeAssetRuntime:
            """Represent fake asset runtime and centralize responsibilities for this module."""
            def generate_pdf_page_images(self, **kwargs):
                """Run generate pdf page images in this workflow."""
                return []
    
            def extract_pdf_region_image(self, **kwargs):
                """Extract pdf region image for this workflow."""
                return b""
    
            def parse_annotation_to_dataframe(self, **kwargs):
                """Parse annotation to dataframe for this workflow."""
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
        """Run test pdf asset workflow usa runtime de assets in this workflow."""
        called = {"generate": {}, "extract": {}, "parse": {}}
        expected_df = pd.DataFrame([{"col_1": "ok"}])
    
        class FakeImageRuntime:
            """Represent fake image runtime and centralize responsibilities for this module."""
            async def pdf_bytes_to_images(self, **kwargs):
                """Run pdf bytes to images in this workflow."""
                _ = kwargs
                return []
    
        class FakeAssetRuntime:
            """Represent fake asset runtime and centralize responsibilities for this module."""
            def generate_pdf_page_images(self, **kwargs):
                """Run generate pdf page images in this workflow."""
                called["generate"].update(kwargs)
                return ["/static/previews/x/page-1.png"]
    
            def extract_pdf_region_image(self, **kwargs):
                """Extract pdf region image for this workflow."""
                called["extract"].update(kwargs)
                return b"img"
    
            def parse_annotation_to_dataframe(self, **kwargs):
                """Parse annotation to dataframe for this workflow."""
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




