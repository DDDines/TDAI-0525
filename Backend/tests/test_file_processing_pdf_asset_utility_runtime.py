import pandas as pd

from Backend.testing.runtime_apis import file_processing


def test_generate_pdf_page_images_impl_usa_runtime(monkeypatch):
    called = {}

    class FakeRuntime:
        def generate_pdf_page_images(self, **kwargs):
            called.update(kwargs)
            return ["/static/previews/x/page-1.png"]

        def extract_pdf_region_image(self, **kwargs):
            return b""

        def parse_annotation_to_dataframe(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(file_processing, "_pdf_asset_utility_runtime", FakeRuntime())

    result = file_processing._generate_pdf_page_images_impl("C:/tmp/file.pdf", "x")

    assert result == ["/static/previews/x/page-1.png"]
    assert called["file_path"] == "C:/tmp/file.pdf"
    assert called["file_id"] == "x"


def test_extract_pdf_region_image_impl_usa_runtime(monkeypatch):
    called = {}

    class FakeRuntime:
        def generate_pdf_page_images(self, **kwargs):
            return []

        def extract_pdf_region_image(self, **kwargs):
            called.update(kwargs)
            return b"img"

        def parse_annotation_to_dataframe(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(file_processing, "_pdf_asset_utility_runtime", FakeRuntime())

    result = file_processing._extract_pdf_region_image_impl(
        file_path="C:/tmp/file.pdf",
        page_number=3,
        region=[1.0, 2.0, 3.0, 4.0],
        dpi=220,
    )

    assert result == b"img"
    assert called["file_path"] == "C:/tmp/file.pdf"
    assert called["page_number"] == 3
    assert called["region"] == [1.0, 2.0, 3.0, 4.0]
    assert called["dpi"] == 220


def test_parse_annotation_to_dataframe_impl_usa_runtime(monkeypatch):
    called = {}
    expected_df = pd.DataFrame([{"col_1": "value"}])

    class FakeRuntime:
        def generate_pdf_page_images(self, **kwargs):
            return []

        def extract_pdf_region_image(self, **kwargs):
            return b""

        def parse_annotation_to_dataframe(self, **kwargs):
            called.update(kwargs)
            return expected_df

    monkeypatch.setattr(file_processing, "_pdf_asset_utility_runtime", FakeRuntime())
    annotation = object()

    result = file_processing._parse_annotation_to_dataframe_impl(
        annotation=annotation,
        vertical_tolerance=9,
    )

    assert result.equals(expected_df)
    assert called["annotation"] is annotation
    assert called["vertical_tolerance"] == 9

