import pytest
from pathlib import Path

from Backend.services.file_processing_service import extract_data_from_single_page


def test_ocr_extraction_on_scanned_pdf():
    pdf_path = Path(__file__).resolve().parent / "test_assets" / "scanned.pdf"
    if not pdf_path.exists():
        pytest.skip("Sample scanned PDF not available")

    result = extract_data_from_single_page(str(pdf_path), 1)
    assert result["headers"], "Headers should not be empty"
    assert result["rows"], "Rows should not be empty"
    assert len(result["rows"][0]) == len(result["headers"])
