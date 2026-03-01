import pandas as pd

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    def test_generate_pdf_page_images_impl_usa_runtime(monkeypatch):
        called = {}
    
        def _fake_generate_pdf_page_images(self, **kwargs):
            _ = self
            called.update(kwargs)
            return ["/static/previews/x/page-1.png"]
    
        monkeypatch.setattr(
            file_processing.PdfAssetUtilityRuntime,
            "generate_pdf_page_images",
            _fake_generate_pdf_page_images,
        )
    
        result = file_processing._FileProcessingImplementation._generate_pdf_page_images_impl(
            "C:/tmp/file.pdf",
            "x",
        )
    
        assert result == ["/static/previews/x/page-1.png"]
        assert called["file_path"] == "C:/tmp/file.pdf"
        assert called["file_id"] == "x"

    def test_extract_pdf_region_image_impl_usa_runtime(monkeypatch):
        called = {}
    
        def _fake_extract_pdf_region_image(self, **kwargs):
            _ = self
            called.update(kwargs)
            return b"img"
    
        monkeypatch.setattr(
            file_processing.PdfAssetUtilityRuntime,
            "extract_pdf_region_image",
            _fake_extract_pdf_region_image,
        )
    
        result = file_processing._FileProcessingImplementation._extract_pdf_region_image_impl(
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
    
        def _fake_parse_annotation_to_dataframe(self, **kwargs):
            _ = self
            called.update(kwargs)
            return expected_df
    
        monkeypatch.setattr(
            file_processing.PdfAssetUtilityRuntime,
            "parse_annotation_to_dataframe",
            _fake_parse_annotation_to_dataframe,
        )
        annotation = object()
    
        result = file_processing._FileProcessingImplementation._parse_annotation_to_dataframe_impl(
            annotation=annotation,
            vertical_tolerance=9,
        )
    
        assert result.equals(expected_df)
        assert called["annotation"] is annotation
        assert called["vertical_tolerance"] == 9

test_generate_pdf_page_images_impl_usa_runtime = _TopLevelFunctionSurface.test_generate_pdf_page_images_impl_usa_runtime
test_extract_pdf_region_image_impl_usa_runtime = _TopLevelFunctionSurface.test_extract_pdf_region_image_impl_usa_runtime
test_parse_annotation_to_dataframe_impl_usa_runtime = _TopLevelFunctionSurface.test_parse_annotation_to_dataframe_impl_usa_runtime






