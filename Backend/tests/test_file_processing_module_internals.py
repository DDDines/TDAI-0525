"""Focused internals coverage for file processing runtime module."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import HTTPException

from Backend.testing.runtime_apis import file_processing


class _UploadFileStub:
    """Minimal async upload-file stub."""

    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content
        self.closed = False

    async def read(self):
        return self._content

    async def close(self):
        self.closed = True


class _TopLevelFunctionSurface:
    """Represent top level function surface and centralize responsibilities for this module."""

    def test_file_processing_impl_path_and_pdf_password_helpers(tmp_path, monkeypatch):
        """Cover storage-path resolution and password-error heuristics."""
        impl = file_processing._FileProcessingImplementation

        absolute = tmp_path / "a.pdf"
        assert impl._resolve_storage_path(absolute) == absolute
        backend_relative = impl._resolve_storage_path(Path("Backend/static/uploads"))
        assert str(backend_relative).lower().endswith("backend\\static\\uploads")

        class PasswordError(Exception):
            pass

        assert impl._is_pdf_password_error(PasswordError("requires password")) is True
        assert impl._is_pdf_password_error(RuntimeError("decrypt pdf failed")) is True
        assert impl._is_pdf_password_error(RuntimeError("other")) is False

    @pytest.mark.asyncio
    async def test_file_processing_impl_save_and_delete_catalog(tmp_path, monkeypatch):
        """Save and delete uploaded catalog files through the implementation helpers."""
        monkeypatch.setattr(file_processing.settings, "UPLOAD_DIRECTORY", str(tmp_path), raising=False)
        monkeypatch.setattr(file_processing.settings, "MAX_UPLOAD_BYTES", 1024, raising=False)

        upload = _UploadFileStub("catalogo.pdf", b"%PDF-1.4 bytes")
        catalog_file = await file_processing._FileProcessingImplementation._save_uploaded_catalog_impl(
            file=upload,
            fornecedor_id=9,
        )

        stored_path = tmp_path / "catalogs" / catalog_file.stored_filename
        assert stored_path.exists() is True
        assert catalog_file.original_filename == "catalogo.pdf"
        assert catalog_file.fornecedor_id == 9
        assert upload.closed is True

        file_processing._FileProcessingImplementation._delete_catalog_file_impl(catalog_file.stored_filename)
        assert stored_path.exists() is False

    @pytest.mark.asyncio
    async def test_file_processing_impl_save_catalog_rejects_invalid_signature_and_oversized_upload(
        tmp_path,
        monkeypatch,
    ):
        """Reject invalid file signatures and oversize uploads before persisting them."""
        monkeypatch.setattr(file_processing.settings, "UPLOAD_DIRECTORY", str(tmp_path), raising=False)

        invalid_upload = _UploadFileStub("catalogo.pdf", b"not-a-pdf")
        monkeypatch.setattr(file_processing.settings, "MAX_UPLOAD_BYTES", 1024, raising=False)
        with pytest.raises(HTTPException) as invalid_exc:
            await file_processing._FileProcessingImplementation._save_uploaded_catalog_impl(
                file=invalid_upload,
                fornecedor_id=1,
            )
        assert invalid_exc.value.status_code == 400
        assert invalid_exc.value.detail["code"] == "FILE_SIGNATURE_INVALID"
        assert invalid_upload.closed is True

        large_upload = _UploadFileStub("catalogo.pdf", b"%PDF-1.4 payload")
        monkeypatch.setattr(file_processing.settings, "MAX_UPLOAD_BYTES", 4, raising=False)
        with pytest.raises(HTTPException) as large_exc:
            await file_processing._FileProcessingImplementation._save_uploaded_catalog_impl(
                file=large_upload,
                fornecedor_id=2,
            )
        assert large_exc.value.status_code == 413
        assert large_exc.value.detail["code"] == "FILE_TOO_LARGE"
        assert large_upload.closed is True

    def test_line_normalization_runtime_covers_remaining_branches():
        """Cover invalid bbox, token heuristics and split edge cases."""
        runtime = file_processing.LineNormalizationRuntime()

        assert runtime.norm_text(" Valor ") == "valor"
        assert runtime.normalizar_mapeamento_usuario(None, {"a": 1}) == {}
        assert runtime.coerce_region_bbox(["x"], 100, 100) == (None, None)
        assert runtime.coerce_region_bbox([10, 10, 5, 5], 100, 100) == (None, "invalid_after_clamp")
        assert runtime.token_looks_like_code("ABC123") is True
        assert runtime.token_looks_like_code("LH") is True
        assert runtime.token_looks_like_code("codigo longo demais para aceitar 1234567890") is False
        assert runtime.split_sku_nome_auto("") == (None, None)
        assert runtime.split_sku_nome_auto("SKU123") == ("SKU123", None)

    def test_pdf_runtime_internal_row_and_identity_filters():
        """Cover row extraction heuristics and product identity filters."""
        runtime = file_processing.PdfIngestionRuntime()

        rows = runtime._extract_structured_rows_from_text(
            "SKU123 Produto Teste\n"
            "Material: Aco carbono\n"
            "ABC123   Descricao por colunas"
        )
        assert rows[0]["sku_original"] == "SKU123"
        assert rows[1]["col_0"] == "ABC123"

        low_df = pd.DataFrame([{"col_0": "-", "col_1": ""}])
        assert runtime._is_low_confidence_dataframe(low_df) is True
        good_df = pd.DataFrame([{"col_0": "SKU123", "col_1": "Produto de freio"}])
        assert runtime._is_low_confidence_dataframe(good_df) is False

        produtos = []
        runtime._append_produto(produtos, {"motivo_descarte": "sem identidade"}, None)
        runtime._append_produto(produtos, {"nome_base": "12"}, None)
        runtime._append_produto(produtos, {"nome_base": "SKU123 Produto", "sku_original": "SKU123"}, 7)
        assert len(produtos) == 1
        assert produtos[0]["product_type_id"] == 7
        assert runtime._looks_like_toc_or_page_marker("Indice") is True
        assert runtime._looks_like_toc_or_page_marker("Conteudo da Pagina 2") is False
        assert runtime._is_weak_name_only_identity("123") is True
        assert runtime._is_weak_name_only_identity("Reservatorio de Ar") is False

    @pytest.mark.asyncio
    async def test_tabular_ingestion_runtime_error_paths(monkeypatch):
        """Cover exception branches in Excel and CSV ingestion."""
        runtime = file_processing.TabularIngestionRuntime()

        monkeypatch.setattr(file_processing.pd, "ExcelFile", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("excel fail")))
        result = await runtime.processar_arquivo_excel(b"PK\x03\x04xlsx")
        assert result[0]["erro_processamento_excel"] == "Falha ao ler arquivo Excel: excel fail"

        original_decode = bytes.decode

        class _BrokenBytes(bytes):
            def decode(self, encoding="utf-8", errors="strict"):
                raise RuntimeError("csv fail")

        result = await runtime.processar_arquivo_csv(_BrokenBytes(b"x"))
        assert result[0]["erro_processamento_csv"] == "Falha ao ler arquivo CSV: csv fail"

    @pytest.mark.asyncio
    async def test_file_processing_security_validation_returns_structured_error_payloads(monkeypatch):
        """Cover structured validation payloads across Excel/CSV/PDF parse and preview entrypoints."""
        monkeypatch.setattr(file_processing.settings, "MAX_UPLOAD_BYTES", 1024, raising=False)

        preview_runtime = file_processing.TabularPreviewRuntime()
        assert (
            await preview_runtime.preview_arquivo_excel(b"not-excel", max_rows=2)
        )["error_code"] == "FILE_SIGNATURE_INVALID"
        assert (
            await preview_runtime.preview_arquivo_csv(b"\x00\x01bin", max_rows=2)
        )["error_code"] == "FILE_SIGNATURE_INVALID"

        ingestion_runtime = file_processing.TabularIngestionRuntime()
        assert (
            await ingestion_runtime.processar_arquivo_excel(b"not-excel")
        )[0]["error_code"] == "FILE_SIGNATURE_INVALID"
        assert (
            await ingestion_runtime.processar_arquivo_csv(b"\x00\x01bin")
        )[0]["error_code"] == "FILE_SIGNATURE_INVALID"

        pdf_runtime = file_processing.PdfIngestionRuntime()
        assert (
            await pdf_runtime.processar_arquivo_pdf(b"not-pdf")
        )[0]["error_code"] == "FILE_SIGNATURE_INVALID"

    @pytest.mark.asyncio
    async def test_file_processing_security_helper_branches_cover_fallback_limits_and_explicit_catches(
        monkeypatch,
    ):
        """Cover fallback helpers and explicit catch branches introduced by upload hardening."""
        impl = file_processing._FileProcessingImplementation
        error = file_processing.CatalogImportSanitizationService.FileSecurityValidationError(
            code="FILE_TOO_LARGE",
            detail="payload grande",
        )

        monkeypatch.setattr(file_processing.settings, "MAX_UPLOAD_BYTES", "bad-value", raising=False)
        assert impl._resolve_max_upload_bytes() == 25 * 1024 * 1024
        http_exc = impl._build_file_security_http_exception(error)
        assert http_exc.status_code == 413
        assert http_exc.detail["code"] == "FILE_TOO_LARGE"

        upload = _UploadFileStub("catalogo.pdf", b"%PDF-1.4")
        monkeypatch.setattr(
            impl,
            "_validate_file_payload",
            lambda **kwargs: (_ for _ in ()).throw(error),
        )
        with pytest.raises(HTTPException):
            await impl._save_uploaded_catalog_impl(file=upload, fornecedor_id=3)
        assert upload.closed is True

        tabular_runtime = file_processing.TabularIngestionEngineRuntime()
        assert (
            await tabular_runtime.processar_arquivo_excel(b"%PDF-1.4")
        )[0]["error_code"] == "FILE_TOO_LARGE"
        assert (
            await tabular_runtime.processar_arquivo_csv(b"%PDF-1.4")
        )[0]["error_code"] == "FILE_TOO_LARGE"

        preview_runtime = file_processing.TabularPreviewEngineRuntime()
        assert (
            await preview_runtime.preview_arquivo_excel(b"%PDF-1.4")
        )["error_code"] == "FILE_TOO_LARGE"
        assert (
            await preview_runtime.preview_arquivo_csv(b"%PDF-1.4")
        )["error_code"] == "FILE_TOO_LARGE"

        pdf_runtime = file_processing.PdfIngestionRuntime()
        assert (
            await pdf_runtime.processar_arquivo_pdf(b"%PDF-1.4")
        )[0]["error_code"] == "FILE_TOO_LARGE"


test_file_processing_impl_path_and_pdf_password_helpers = (
    _TopLevelFunctionSurface.test_file_processing_impl_path_and_pdf_password_helpers
)
test_file_processing_impl_save_and_delete_catalog = (
    _TopLevelFunctionSurface.test_file_processing_impl_save_and_delete_catalog
)
test_line_normalization_runtime_covers_remaining_branches = (
    _TopLevelFunctionSurface.test_line_normalization_runtime_covers_remaining_branches
)
test_pdf_runtime_internal_row_and_identity_filters = (
    _TopLevelFunctionSurface.test_pdf_runtime_internal_row_and_identity_filters
)
test_tabular_ingestion_runtime_error_paths = (
    _TopLevelFunctionSurface.test_tabular_ingestion_runtime_error_paths
)
test_file_processing_impl_save_catalog_rejects_invalid_signature_and_oversized_upload = (
    _TopLevelFunctionSurface.test_file_processing_impl_save_catalog_rejects_invalid_signature_and_oversized_upload
)
test_file_processing_security_validation_returns_structured_error_payloads = (
    _TopLevelFunctionSurface.test_file_processing_security_validation_returns_structured_error_payloads
)
test_file_processing_security_helper_branches_cover_fallback_limits_and_explicit_catches = (
    _TopLevelFunctionSurface.test_file_processing_security_helper_branches_cover_fallback_limits_and_explicit_catches
)
