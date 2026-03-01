import pytest
from pathlib import Path

from Backend.application.services.service_container import ServiceContainer

file_processing_service = ServiceContainer().file_processing


def test_ocr_extraction_on_scanned_pdf():
    pdf_path = Path(__file__).resolve().parent / "test_assets" / "scanned.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample scanned PDF not available")

    result = file_processing_service.extract_data_from_single_page(str(pdf_path), 1)
    assert result["headers"], "Headers should not be empty"
    assert result["rows"], "Rows should not be empty"
    assert len(result["rows"][0]) == len(result["headers"])


def test_region_extraction_does_not_explode_structure():
    pdf_path = Path(__file__).resolve().parent / "test_assets" / "scanned.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample scanned PDF not available")

    df = file_processing_service.extract_data_from_pdf_region(str(pdf_path), 1, None)
    assert not df.empty
    assert len(df.columns) <= 30
    assert len(df.index) <= 2000

