from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_ingest_service import (
    CatalogImportIngestService,
)


class _UploadFileStub:
    def __init__(self, *, filename: str, content: bytes = b"data"):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


class _CrudFornecedoresStub:
    def __init__(self, fornecedor=None):
        self._fornecedor = fornecedor

    def get_fornecedor(self, db, fornecedor_id):
        _ = (db, fornecedor_id)
        return self._fornecedor


class _CrudProdutosStub:
    def __init__(self):
        self.bulk_calls = []

    def create_produtos_bulk(self, db, produtos, user_id):
        _ = db
        self.bulk_calls.append((produtos, user_id))
        created = [SimpleNamespace(id=77)]
        return created, [], []


class _CrudUsoIAStub:
    def __init__(self):
        self.calls = []

    def create_registro_uso_ia(self, db, payload):
        _ = db
        self.calls.append(payload.data)


class _CrudHistoricoStub:
    def __init__(self):
        self.calls = []

    def create_registro_historico(self, db, payload):
        _ = db
        self.calls.append(payload.data)


class _FileProcessingStub:
    def __init__(self):
        self.responses = {
            ".xlsx": [],
            ".csv": [],
            ".pdf": [],
        }

    async def processar_arquivo_excel(self, content, mapping_dict):
        _ = (content, mapping_dict)
        return self.responses[".xlsx"]

    async def processar_arquivo_csv(self, content, mapping_dict):
        _ = (content, mapping_dict)
        return self.responses[".csv"]

    async def processar_arquivo_pdf(self, content, mapping_dict):
        _ = (content, mapping_dict)
        return self.responses[".pdf"]


class _Payload:
    def __init__(self, **kwargs):
        self.data = kwargs


class _ProdutoCreate:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SchemasStub:
    ProdutoCreate = _ProdutoCreate
    RegistroUsoIACreate = _Payload
    RegistroHistoricoCreate = _Payload


class _TipoAcaoEnumStub:
    CRIACAO_PRODUTO = "CRIACAO_PRODUTO"


class _TipoAcaoSistemaEnumStub:
    CRIACAO = "CRIACAO"


class _ModelsStub:
    TipoAcaoEnum = _TipoAcaoEnumStub
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


def _build_service(*, fornecedor=None):
    crud_fornecedores = _CrudFornecedoresStub(fornecedor=fornecedor)
    crud_produtos = _CrudProdutosStub()
    crud_uso_ia = _CrudUsoIAStub()
    crud_historico = _CrudHistoricoStub()
    file_processing = _FileProcessingStub()

    service = CatalogImportIngestService(
        schemas=_SchemasStub,
        models=_ModelsStub,
        crud_fornecedores=crud_fornecedores,
        crud_produtos=crud_produtos,
        crud_uso_ia=crud_uso_ia,
        crud_historico=crud_historico,
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
    return service, file_processing, crud_produtos, crud_uso_ia, crud_historico


def test_importar_catalogo_fornecedor_raises_when_mapping_json_invalid():
    service, *_ = _build_service()

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
    service, *_ = _build_service()

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
    service, file_processing, crud_produtos, crud_uso_ia, crud_historico = _build_service(
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
