"""Module test pipeline use cases.

Contains backend logic related to test pipeline use cases and documents its role in the OOP architecture.
"""

import pytest

from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)
from Backend.application.contracts.pipeline_commands import (
    CatalogImportFinalizeCommand,
    WebEnrichmentStartCommand,
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    async def _dummy_processor(**kwargs):
        """Run dummy processor in this workflow."""
        return kwargs

    @pytest.mark.asyncio
    async def test_catalog_import_use_case_normalizes_payload():
        """Run test catalog import use case normalizes payload in this workflow."""
        use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)
        result = await use_case.execute(
            file_id="10",
            user_id=20,
            product_type_id="3",
            fornecedor_id=8,
            mapping={" col_0 ": " Nome Base ", "": "ignorar", "col_1": ""},
            pages=[1, "2", 2, "3"],
            region=["1.0", 2, 3.5, "4"],
            extraction_mode=" IA ",
        )
    
        assert result["file_id"] == 10
        assert result["user_id"] == 20
        assert result["product_type_id"] == 3
        assert result["fornecedor_id"] == 8
        assert result["mapping"] == {"col_0": "Nome Base"}
        assert result["pages"] == [1, 2, 3]
        assert result["region"] == [1.0, 2.0, 3.5, 4.0]
        assert result["extraction_mode"] == "ia"

    @pytest.mark.asyncio
    async def test_catalog_import_use_case_rejects_invalid_ids():
        """Run test catalog import use case rejects invalid ids in this workflow."""
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
    async def test_catalog_import_use_case_execute_command_normalizes_payload():
        """Run test catalog import use case execute command normalizes payload in this workflow."""
        use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)
        command = CatalogImportFinalizeCommand(
            file_id=10,
            user_id=20,
            product_type_id=3,
            fornecedor_id=8,
            mapping={"col_0": "Nome Base"},
            pages=[1, 2],
            region=[1.0, 2.0, 3.0, 4.0],
        )
        result = await use_case.execute_command(
            command=command,
        )
    
        assert result["file_id"] == 10
        assert result["pages"] == [1, 2]
        assert result["extraction_mode"] == "ocr"

    @pytest.mark.asyncio
    async def test_catalog_import_use_case_rejects_invalid_extraction_mode():
        """Run test catalog import use case rejects invalid extraction mode in this workflow."""
        use_case = CatalogImportProcessingUseCase(processor=_dummy_processor)

        with pytest.raises(ValueError, match="extraction_mode"):
            await use_case.execute(
                file_id=10,
                user_id=20,
                product_type_id=3,
                fornecedor_id=8,
                mapping={"col_0": "Nome Base"},
                pages=[1],
                region=[1.0, 2.0, 3.0, 4.0],
                extraction_mode="auto",
            )

    @pytest.mark.asyncio
    async def test_web_enrichment_use_case_normalizes_search_terms():
        """Run test web enrichment use case normalizes search terms in this workflow."""
        use_case = WebEnrichmentProcessingUseCase(processor=_dummy_processor)
        result = await use_case.execute(
            produto_id="5",
            user_id=9,
            termos_busca_override="   termo de busca   ",
            usar_ia="true",
        )
    
        assert result["produto_id"] == 5
        assert result["user_id"] == 9
        assert result["termos_busca_override"] == "termo de busca"
        assert result["usar_ia"] is True

    @pytest.mark.asyncio
    async def test_web_enrichment_use_case_rejects_invalid_produto_id():
        """Run test web enrichment use case rejects invalid produto id in this workflow."""
        use_case = WebEnrichmentProcessingUseCase(processor=_dummy_processor)
        with pytest.raises(ValueError, match="produto_id"):
            await use_case.execute(
                produto_id=-1,
                user_id=9,
                termos_busca_override=None,
            )

    @pytest.mark.asyncio
    async def test_web_enrichment_use_case_execute_command_normalizes_payload():
        """Run test web enrichment use case execute command normalizes payload in this workflow."""
        use_case = WebEnrichmentProcessingUseCase(processor=_dummy_processor)
        command = WebEnrichmentStartCommand(
            produto_id=12,
            user_id=9,
            termos_busca_override="  abc  ",
            usar_ia=False,
        )
        result = await use_case.execute_command(
            command=command,
        )
    
        assert result["produto_id"] == 12
        assert result["termos_busca_override"] == "abc"
        assert result["usar_ia"] is False

_dummy_processor = _TopLevelFunctionSurface._dummy_processor
test_catalog_import_use_case_normalizes_payload = _TopLevelFunctionSurface.test_catalog_import_use_case_normalizes_payload
test_catalog_import_use_case_rejects_invalid_ids = _TopLevelFunctionSurface.test_catalog_import_use_case_rejects_invalid_ids
test_catalog_import_use_case_execute_command_normalizes_payload = _TopLevelFunctionSurface.test_catalog_import_use_case_execute_command_normalizes_payload
test_catalog_import_use_case_rejects_invalid_extraction_mode = _TopLevelFunctionSurface.test_catalog_import_use_case_rejects_invalid_extraction_mode
test_web_enrichment_use_case_normalizes_search_terms = _TopLevelFunctionSurface.test_web_enrichment_use_case_normalizes_search_terms
test_web_enrichment_use_case_rejects_invalid_produto_id = _TopLevelFunctionSurface.test_web_enrichment_use_case_rejects_invalid_produto_id
test_web_enrichment_use_case_execute_command_normalizes_payload = _TopLevelFunctionSurface.test_web_enrichment_use_case_execute_command_normalizes_payload












