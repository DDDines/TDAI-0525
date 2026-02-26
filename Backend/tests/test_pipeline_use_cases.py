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
async def test_catalog_import_use_case_normalizes_payload():
    use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)
    result = await use_case.execute(
        db_session_factory="factory",
        file_id="10",
        user_id=20,
        product_type_id="3",
        fornecedor_id=8,
        mapping={" col_0 ": " Nome Base ", "": "ignorar", "col_1": ""},
        pages=[1, "2", 2, "3"],
        region=["1.0", 2, 3.5, "4"],
    )

    assert result["file_id"] == 10
    assert result["user_id"] == 20
    assert result["product_type_id"] == 3
    assert result["fornecedor_id"] == 8
    assert result["mapping"] == {"col_0": "Nome Base"}
    assert result["pages"] == [1, 2, 3]
    assert result["region"] == [1.0, 2.0, 3.5, 4.0]


@pytest.mark.asyncio
async def test_catalog_import_use_case_rejects_invalid_ids():
    use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)

    with pytest.raises(ValueError, match="file_id"):
        await use_case.execute(
            file_id=0,
            user_id=1,
            product_type_id=None,
            fornecedor_id=1,
            mapping=None,
            pages=None,
            region=None,
        )


@pytest.mark.asyncio
async def test_web_enrichment_use_case_normalizes_search_terms():
    use_case = WebEnrichmentProcessingUseCase(processor=_dummy_processor)
    result = await use_case.execute(
        db_session_factory="factory",
        produto_id="5",
        user_id=9,
        termos_busca_override="   termo de busca   ",
    )

    assert result["produto_id"] == 5
    assert result["user_id"] == 9
    assert result["termos_busca_override"] == "termo de busca"


@pytest.mark.asyncio
async def test_web_enrichment_use_case_rejects_invalid_produto_id():
    use_case = WebEnrichmentProcessingUseCase(processor=_dummy_processor)
    with pytest.raises(ValueError, match="produto_id"):
        await use_case.execute(
            produto_id=-1,
            user_id=9,
            termos_busca_override=None,
        )
