"""Module test catalog import ingest service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_ingest_service import (
    CatalogImportIngestService,
)


class _UploadFileStub:
    """Class _UploadFileStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, filename: str, content: bytes = b"data"):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.filename = filename
        self._content = content

    async def read(self):
        """Execute read.

        This callable is documented to make behavior explicit for readers.
        """
        return self._content


class _CrudFornecedoresStub:
    """Class _CrudFornecedoresStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, fornecedor=None):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._fornecedor = fornecedor

    def get_fornecedor(self, *, fornecedor_id):
        """Execute get_fornecedor.

        This callable is documented to make behavior explicit for readers.
        """
        _ = fornecedor_id
        return self._fornecedor


class _CrudProdutosStub:
    """Class _CrudProdutosStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.bulk_calls = []

    def create_produtos_bulk(self, *, produtos, user_id):
        """Execute create_produtos_bulk.

        This callable is documented to make behavior explicit for readers.
        """
        self.bulk_calls.append((produtos, user_id))
        created = [SimpleNamespace(id=77)]
        return created, [], []


class _CrudUsoIAStub:
    """Class _CrudUsoIAStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def create_registro_uso_ia(self, *, registro_uso):
        """Execute create_registro_uso_ia.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append(registro_uso.data)


class _CrudHistoricoStub:
    """Class _CrudHistoricoStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def create_registro_historico(self, *, registro_in):
        """Execute create_registro_historico.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append(registro_in.data)


class _FileProcessingStub:
    """Class _FileProcessingStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.responses = {
            ".xlsx": [],
            ".csv": [],
            ".pdf": [],
        }

    async def processar_arquivo_excel(self, content, mapping_dict):
        """Execute processar_arquivo_excel.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (content, mapping_dict)
        return self.responses[".xlsx"]

    async def processar_arquivo_csv(self, content, mapping_dict):
        """Execute processar_arquivo_csv.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (content, mapping_dict)
        return self.responses[".csv"]

    async def processar_arquivo_pdf(self, content, mapping_dict):
        """Execute processar_arquivo_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (content, mapping_dict)
        return self.responses[".pdf"]


class _Payload:
    """Class _Payload.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, **kwargs):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.data = kwargs


class _ProdutoCreate:
    """Class _ProdutoCreate.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, **kwargs):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SchemasStub:
    """Class _SchemasStub.

    Encapsulates one responsibility in the backend architecture.
    """
    ProdutoCreate = _ProdutoCreate
    RegistroUsoIACreate = _Payload
    RegistroHistoricoCreate = _Payload


class _TipoAcaoEnumStub:
    """Class _TipoAcaoEnumStub.

    Encapsulates one responsibility in the backend architecture.
    """
    CRIACAO_PRODUTO = "CRIACAO_PRODUTO"


class _TipoAcaoSistemaEnumStub:
    """Class _TipoAcaoSistemaEnumStub.

    Encapsulates one responsibility in the backend architecture.
    """
    CRIACAO = "CRIACAO"


class _ModelsStub:
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    TipoAcaoEnum = _TipoAcaoEnumStub
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(*, fornecedor=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        fornecedor_repo = _CrudFornecedoresStub(fornecedor=fornecedor)
        produto_repo = _CrudProdutosStub()
        uso_ia_repo = _CrudUsoIAStub()
        historico_repo = _CrudHistoricoStub()
        file_processing = _FileProcessingStub()
    
        service = CatalogImportIngestService(
            schemas=_SchemasStub,
            models=_ModelsStub,
            fornecedor_repo=fornecedor_repo,
            produto_repo=produto_repo,
            uso_ia_repo=uso_ia_repo,
            historico_repo=historico_repo,
            file_processing_service=file_processing,
            normalize_import_issue_item=lambda item: item,
            extract_import_error_reason=lambda item: item.get("motivo_descarte", ""),
            is_non_critical_import_reason=lambda reason: reason == "nao_critico",
            sanitize_produto_extraido=lambda prod: prod,
            classificar_qualidade_linha_produto=lambda cleaned: {
                "decision": "accept",
                "score": 100,
                "reason": None,
            },
            json_module=__import__("json"),
        )
        return (
            service,
            file_processing,
            fornecedor_repo,
            produto_repo,
            uso_ia_repo,
            historico_repo,
        )

    def test_importar_catalogo_fornecedor_raises_when_mapping_json_invalid():
        """Execute test_importar_catalogo_fornecedor_raises_when_mapping_json_invalid.

        This callable is documented to make behavior explicit for readers.
        """
        service, _, _, _, _, _ = _build_service()
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                service.importar_catalogo_fornecedor(
                    fornecedor_id=1,
                    file=_UploadFileStub(filename="catalogo.pdf"),
                    mapeamento_colunas_usuario="{nao-json}",
                    current_user=SimpleNamespace(id=10),
                )
            )
    
        assert exc.value.status_code == 400

    def test_importar_catalogo_fornecedor_raises_when_extension_not_supported():
        """Execute test_importar_catalogo_fornecedor_raises_when_extension_not_supported.

        This callable is documented to make behavior explicit for readers.
        """
        service, _, _, _, _, _ = _build_service()
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                service.importar_catalogo_fornecedor(
                    fornecedor_id=1,
                    file=_UploadFileStub(filename="catalogo.txt"),
                    mapeamento_colunas_usuario=None,
                    current_user=SimpleNamespace(id=10),
                )
            )
    
        assert exc.value.status_code == 400

    def test_importar_catalogo_fornecedor_creates_products_and_logs():
        """Execute test_importar_catalogo_fornecedor_creates_products_and_logs.

        This callable is documented to make behavior explicit for readers.
        """
        service, file_processing, fornecedor_repo, crud_produtos, crud_uso_ia, crud_historico = _build_service(
            fornecedor=SimpleNamespace(default_column_mapping={"col_1": "Nome Base"})
        )
        file_processing.responses[".pdf"] = [
            {
                "nome_base": "Peca A",
                "sku_original": "SKU-1",
                "ean_original": "123",
                "descricao_original": "Descricao",
                "marca": "Marca",
                "categoria_original": "Cat",
            },
            {"motivo_descarte": "erro_teste"},
        ]
    
        result = asyncio.run(
            service.importar_catalogo_fornecedor(
                fornecedor_id=2,
                file=_UploadFileStub(filename="catalogo.pdf"),
                mapeamento_colunas_usuario=None,
                current_user=SimpleNamespace(id=99),
            )
        )
    
        assert len(result["produtos_criados"]) == 1
        assert len(result["erros"]) == 1
        assert len(crud_produtos.bulk_calls) == 1
        assert len(crud_uso_ia.calls) == 1
        assert len(crud_historico.calls) == 1

_build_service = _TopLevelFunctionSurface._build_service
test_importar_catalogo_fornecedor_raises_when_mapping_json_invalid = _TopLevelFunctionSurface.test_importar_catalogo_fornecedor_raises_when_mapping_json_invalid
test_importar_catalogo_fornecedor_raises_when_extension_not_supported = _TopLevelFunctionSurface.test_importar_catalogo_fornecedor_raises_when_extension_not_supported
test_importar_catalogo_fornecedor_creates_products_and_logs = _TopLevelFunctionSurface.test_importar_catalogo_fornecedor_creates_products_and_logs






