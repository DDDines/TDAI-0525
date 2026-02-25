import pytest

from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)


async def _dummy_processor(**kwargs):
    return kwargs


@pytest.mark.asyncio
async def test_catalog_import_use_case_delegates_to_processor():
    use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)
    result = await use_case.execute(file_id=10, user_id=20)
    assert result["file_id"] == 10
    assert result["user_id"] == 20


@pytest.mark.asyncio
async def test_web_enrichment_use_case_delegates_to_processor():
    use_case = WebEnrichmentProcessingUseCase(processor=_dummy_processor)
    result = await use_case.execute(produto_id=5, user_id=9)
    assert result["produto_id"] == 5
    assert result["user_id"] == 9
