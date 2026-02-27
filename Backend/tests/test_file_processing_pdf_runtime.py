import pytest

import Backend.services.file_processing_service as file_processing


@pytest.mark.asyncio
async def test_pdf_runtime_delega_para_legacy(monkeypatch):
    runtime = file_processing._PdfIngestionRuntime()
    called = {}

    async def fake_legacy(**kwargs):
        called.update(kwargs)
        return [{"ok": True}]

    monkeypatch.setattr(
        file_processing,
        "_processar_arquivo_pdf_legacy_impl",
        fake_legacy,
    )

    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"pdf-bytes",
        mapeamento_colunas_usuario={"col_0": "nome_base"},
        usar_llm=False,
        product_type_id=7,
        pages=[2, 3],
        region=[0.1, 0.1, 0.9, 0.9],
    )

    assert result == [{"ok": True}]
    assert called["conteudo_arquivo"] == b"pdf-bytes"
    assert called["mapeamento_colunas_usuario"] == {"col_0": "nome_base"}
    assert called["usar_llm"] is False
    assert called["product_type_id"] == 7
    assert called["pages"] == [2, 3]
    assert called["region"] == [0.1, 0.1, 0.9, 0.9]


@pytest.mark.asyncio
async def test_processar_arquivo_pdf_impl_usa_runtime(monkeypatch):
    called = {}

    class FakeRuntime:
        async def processar_arquivo_pdf(self, **kwargs):
            called.update(kwargs)
            return [{"source": "runtime"}]

    monkeypatch.setattr(
        file_processing,
        "_pdf_ingestion_runtime",
        FakeRuntime(),
    )

    result = await file_processing._processar_arquivo_pdf_impl(
        conteudo_arquivo=b"abc",
        mapeamento_colunas_usuario={"col_1": "sku_original"},
        usar_llm=True,
        product_type_id=11,
        pages=[1],
        region=None,
    )

    assert result == [{"source": "runtime"}]
    assert called["conteudo_arquivo"] == b"abc"
    assert called["mapeamento_colunas_usuario"] == {"col_1": "sku_original"}
    assert called["usar_llm"] is True
    assert called["product_type_id"] == 11
    assert called["pages"] == [1]
    assert called["region"] is None
