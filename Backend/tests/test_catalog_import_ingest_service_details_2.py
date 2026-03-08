from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from Backend.application.services.catalog_import_ingest_service import (
    CatalogImportIngestService,
)


class _UploadFileStub:
    def __init__(self, *, filename: str, content: bytes = b"x"):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


class _FileProcessingStub:
    def __init__(self):
        self.responses = {".xlsx": [], ".csv": [], ".pdf": []}

    async def processar_arquivo_excel(self, content, mapping_dict):
        _ = (content, mapping_dict)
        return self.responses[".xlsx"]

    async def processar_arquivo_csv(self, content, mapping_dict):
        _ = (content, mapping_dict)
        return self.responses[".csv"]

    async def processar_arquivo_pdf(self, content, mapping_dict):
        _ = (content, mapping_dict)
        return self.responses[".pdf"]


class _FornecedorRepoStub:
    def __init__(self, fornecedor=None):
        self._fornecedor = fornecedor

    def get_fornecedor(self, *, fornecedor_id):
        _ = fornecedor_id
        return self._fornecedor


class _ProdutoRepoStub:
    def __init__(self, *, created=None, updated=None, dup_errors=None):
        self.bulk_calls = []
        self._created = created if created is not None else [SimpleNamespace(id=77)]
        self._updated = updated if updated is not None else []
        self._dup_errors = dup_errors if dup_errors is not None else []

    def create_produtos_bulk(self, *, produtos, user_id):
        self.bulk_calls.append((produtos, user_id))
        return self._created, self._updated, self._dup_errors


class _RepoRecorder:
    def __init__(self):
        self.calls = []

    def create_registro_uso_ia(self, *, registro_uso):
        self.calls.append(registro_uso.data)

    def create_registro_historico(self, *, registro_in):
        self.calls.append(registro_in.data)


class _Payload:
    def __init__(self, **kwargs):
        self.data = kwargs


class _ProdutoCreate:
    should_fail = False

    def __init__(self, **kwargs):
        if _ProdutoCreate.should_fail:
            raise RuntimeError("schema invalido")
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


def _build_service(*, fornecedor=None, quality=None, produto_repo=None, sanitizer=None):
    file_processing = _FileProcessingStub()
    fornecedor_repo = _FornecedorRepoStub(fornecedor=fornecedor)
    produto_repo = produto_repo or _ProdutoRepoStub()
    uso_ia_repo = _RepoRecorder()
    historico_repo = _RepoRecorder()
    service = CatalogImportIngestService(
        schemas=_SchemasStub,
        models=_ModelsStub,
        fornecedor_repo=fornecedor_repo,
        produto_repo=produto_repo,
        uso_ia_repo=uso_ia_repo,
        historico_repo=historico_repo,
        file_processing_service=file_processing,
        normalize_import_issue_item=lambda item: dict(item),
        extract_import_error_reason=lambda item: str(item.get("motivo_descarte", "")),
        is_non_critical_import_reason=lambda reason: reason == "nao_critico",
        sanitize_produto_extraido=sanitizer or (lambda prod: dict(prod)),
        classificar_qualidade_linha_produto=quality or (lambda cleaned: {"decision": "accept", "score": 100, "reason": None}),
        json_module=__import__("json"),
    )
    return service, file_processing, produto_repo, uso_ia_repo, historico_repo


def test_append_issue_and_quarantine_helpers_cover_non_critical_paths():
    service, _, _, _, _ = _build_service()
    erros = []
    ignored = []
    quarantine = []

    service._append_import_issue(
        item={"motivo_descarte": "nao_critico"},
        erros=erros,
        ignored_non_critical=ignored,
    )
    service._append_quarantine_issue(
        item={"motivo_descarte": "quarentena"},
        quarantine_non_critical=quarantine,
    )

    assert erros == []
    assert ignored == [{"motivo_descarte": "nao_critico"}]
    assert quarantine == [{"motivo_descarte": "quarentena"}]


def test_process_file_by_extension_supports_excel_and_csv():
    service, file_processing, _, _, _ = _build_service()
    file_processing.responses[".xlsx"] = [{"from": "excel"}]
    file_processing.responses[".csv"] = [{"from": "csv"}]

    excel = asyncio.run(service._process_file_by_extension(content=b"x", ext=".xlsx", mapping_dict=None))
    csv = asyncio.run(service._process_file_by_extension(content=b"x", ext=".csv", mapping_dict={"a": "b"}))

    assert excel == [{"from": "excel"}]
    assert csv == [{"from": "csv"}]


def test_process_file_by_extension_supports_xls_alias():
    service, file_processing, _, _, _ = _build_service()
    file_processing.responses[".xlsx"] = [{"from": "excel-xls"}]

    result = asyncio.run(
        service._process_file_by_extension(content=b"x", ext=".xls", mapping_dict=None)
    )

    assert result == [{"from": "excel-xls"}]


def test_importar_catalogo_fornecedor_handles_discard_and_quarantine_without_bulk_insert():
    decisions = iter(
        [
            {"decision": "discard", "score": 10, "reason": "nao_critico"},
            {"decision": "quarantine", "score": 20, "reason": "score baixo"},
        ]
    )
    service, file_processing, produto_repo, uso_ia_repo, historico_repo = _build_service(
        quality=lambda cleaned: next(decisions)
    )
    file_processing.responses[".pdf"] = [
        {"nome_base": "linha 1"},
        {"nome_base": "linha 2"},
    ]

    result = asyncio.run(
        service.importar_catalogo_fornecedor(
            fornecedor_id=5,
            file=_UploadFileStub(filename="catalogo.pdf"),
            mapeamento_colunas_usuario=None,
            current_user=SimpleNamespace(id=9),
        )
    )

    assert result["produtos_criados"] == []
    assert produto_repo.bulk_calls == []
    assert uso_ia_repo.calls == []
    assert historico_repo.calls == []
    assert result["erros"][0]["motivo_descarte"] == "nao_critico"
    assert result["erros"][1]["classificacao"] == "quarentena"


def test_importar_catalogo_fornecedor_handles_schema_failure_and_duplicate_errors():
    _ProdutoCreate.should_fail = True
    try:
        produto_repo = _ProdutoRepoStub(dup_errors=[{"motivo_descarte": "duplicado"}])
        service, file_processing, produto_repo, _, _ = _build_service(
            produto_repo=produto_repo,
            sanitizer=lambda prod: {"nome_base": "falha"},
        )
        file_processing.responses[".csv"] = [{"nome_base": "linha"}]

        result = asyncio.run(
            service.importar_catalogo_fornecedor(
                fornecedor_id=5,
                file=_UploadFileStub(filename="catalogo.csv"),
                mapeamento_colunas_usuario=None,
                current_user=SimpleNamespace(id=9),
            )
        )

        assert produto_repo.bulk_calls == []
        assert any("Erro ao converter linha: schema invalido" in err["motivo_descarte"] for err in result["erros"])
    finally:
        _ProdutoCreate.should_fail = False


def test_importar_catalogo_fornecedor_uses_supplier_mapping_and_duplicate_error():
    produto_repo = _ProdutoRepoStub(dup_errors=[{"motivo_descarte": "duplicado"}])
    service, file_processing, produto_repo, uso_ia_repo, historico_repo = _build_service(
        fornecedor=SimpleNamespace(default_column_mapping={"coluna": "nome_base"}),
        produto_repo=produto_repo,
    )
    file_processing.responses[".csv"] = [{"nome_base": "Produto csv"}]

    result = asyncio.run(
        service.importar_catalogo_fornecedor(
            fornecedor_id=5,
            file=_UploadFileStub(filename="catalogo.csv"),
            mapeamento_colunas_usuario=None,
            current_user=SimpleNamespace(id=12),
        )
    )

    assert len(produto_repo.bulk_calls) == 1
    assert len(uso_ia_repo.calls) == 1
    assert len(historico_repo.calls) == 1
    assert result["produtos_criados"][0].id == 77
    assert result["erros"][-1]["motivo_descarte"] == "duplicado"
