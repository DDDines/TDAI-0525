import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


@pytest.mark.asyncio
async def test_pdf_asset_workflow_usa_runtime_de_conversao():
    called = {}

    class FakeImageRuntime:
        async def pdf_bytes_to_images(self, **kwargs):
            called.update(kwargs)
            return ["img64"]

    class FakeAssetRuntime:
        def generate_pdf_page_images(self, **kwargs):
            return []

        def extract_pdf_region_image(self, **kwargs):
            return b""

        def parse_annotation_to_dataframe(self, **kwargs):
            return pd.DataFrame()

    workflow = file_processing._PdfAssetWorkflow(
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
    called = {"generate": {}, "extract": {}, "parse": {}}
    expected_df = pd.DataFrame([{"col_1": "ok"}])

    class FakeImageRuntime:
        async def pdf_bytes_to_images(self, **kwargs):
            _ = kwargs
            return []

    class FakeAssetRuntime:
        def generate_pdf_page_images(self, **kwargs):
            called["generate"].update(kwargs)
            return ["/static/previews/x/page-1.png"]

        def extract_pdf_region_image(self, **kwargs):
            called["extract"].update(kwargs)
            return b"img"

        def parse_annotation_to_dataframe(self, **kwargs):
            called["parse"].update(kwargs)
            return expected_df

    workflow = file_processing._PdfAssetWorkflow(
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

