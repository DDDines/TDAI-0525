"""Module test file processing tabular runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import io

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_tabular_runtime_processa_csv_com_delimitador_semicolon():
        """Execute test_tabular_runtime_processa_csv_com_delimitador_semicolon.

        This callable is documented to make behavior explicit for readers.
        """
        runtime = file_processing.TabularIngestionRuntime()
        csv_bytes = (
            "col_0;col_1\n"
            "1816D 943 666 39 01 Paralama/Estribo;SMC\n"
        ).encode("utf-8")
    
        result = await runtime.processar_arquivo_csv(
            conteudo_arquivo=csv_bytes,
            mapeamento_colunas_usuario={"col_0": "auto:sku_nome", "col_1": "attr:material"},
            product_type_id=4,
        )
    
        assert len(result) == 1
        assert result[0]["sku_original"] == "1816D 943 666 39 01"
        assert result[0]["nome_base"] == "Paralama/Estribo"
        assert result[0]["dynamic_attributes"]["material"] == "SMC"
        assert result[0]["product_type_id"] == 4

    @pytest.mark.asyncio
    async def test_tabular_runtime_processa_excel_com_sheet_especifica():
        """Execute test_tabular_runtime_processa_excel_com_sheet_especifica.

        This callable is documented to make behavior explicit for readers.
        """
        runtime = file_processing.TabularIngestionRuntime()
    
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(
                {
                    "col_0": ["1823D 943 880 70 73 Ponteira do Para-choque"],
                    "col_1": ["Plastico"],
                }
            ).to_excel(writer, sheet_name="pecas", index=False)
            pd.DataFrame({"x": [1]}).to_excel(writer, sheet_name="outros", index=False)
    
        result = await runtime.processar_arquivo_excel(
            conteudo_arquivo=buffer.getvalue(),
            mapeamento_colunas_usuario={"col_0": "auto:sku_nome", "col_1": "attr:material"},
            sheet_name="pecas",
            product_type_id=9,
        )
    
        assert len(result) == 1
        assert result[0]["sku_original"] == "1823D 943 880 70 73"
        assert result[0]["nome_base"] == "Ponteira do Para-choque"
        assert result[0]["dynamic_attributes"]["material"] == "Plastico"
        assert result[0]["product_type_id"] == 9

test_tabular_runtime_processa_csv_com_delimitador_semicolon = _TopLevelFunctionSurface.test_tabular_runtime_processa_csv_com_delimitador_semicolon
test_tabular_runtime_processa_excel_com_sheet_especifica = _TopLevelFunctionSurface.test_tabular_runtime_processa_excel_com_sheet_especifica




