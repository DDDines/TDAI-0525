from __future__ import annotations

import pytest

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)


async def _dummy_processor(**kwargs):
    return kwargs


@pytest.mark.asyncio
async def test_execute_command_accepts_none_product_type_and_default_mode():
    use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)
    command = CatalogImportFinalizeCommand(
        file_id=1,
        user_id=2,
        product_type_id=None,
        fornecedor_id=3,
        mapping=None,
        pages=None,
        region=None,
        extraction_mode=None,
    )

    result = await use_case.execute_command(command=command)

    assert result["product_type_id"] is None
    assert result["mapping"] is None
    assert result["pages"] is None
    assert result["region"] is None
    assert result["extraction_mode"] == "ocr"


@pytest.mark.parametrize(
    ("raw_value", "field_name"),
    [
        ("abc", "file_id"),
        (None, "user_id"),
    ],
)
def test_require_positive_int_rejects_non_numeric_values(raw_value, field_name):
    with pytest.raises(ValueError, match=field_name):
        CatalogImportProcessingUseCase._require_positive_int(raw_value, field_name)


def test_normalize_mapping_rejects_invalid_type_and_empty_payload():
    with pytest.raises(ValueError, match="mapping"):
        CatalogImportProcessingUseCase._normalize_mapping(["x"])

    assert CatalogImportProcessingUseCase._normalize_mapping({"": "x", "a": ""}) is None


def test_normalize_pages_rejects_invalid_type():
    with pytest.raises(ValueError, match="pages"):
        CatalogImportProcessingUseCase._normalize_pages("1,2")


def test_normalize_region_rejects_invalid_shape_and_non_numeric_values():
    with pytest.raises(ValueError, match="lista de 4 numeros"):
        CatalogImportProcessingUseCase._normalize_region("1,2,3,4")

    with pytest.raises(ValueError, match="exatamente 4"):
        CatalogImportProcessingUseCase._normalize_region([1, 2, 3])

    with pytest.raises(ValueError, match="apenas numeros"):
        CatalogImportProcessingUseCase._normalize_region([1, 2, 3, "x"])


def test_normalize_extraction_mode_defaults_blank_to_ocr():
    assert CatalogImportProcessingUseCase._normalize_extraction_mode("") == "ocr"
    assert CatalogImportProcessingUseCase._normalize_extraction_mode("   ") == "ocr"
