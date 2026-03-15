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
        assert backend_relative.as_posix().lower().endswith("backend/static/uploads")

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

        monkeypatch.setattr(
            file_processing.TabularIngestionEngineRuntime,
            "_parse_excel_records_in_subprocess",
            lambda self, **kwargs: {
                "ok": False,
                "error_code": "FILE_PARSE_UNSAFE",
                "error": "excel fail",
            },
        )
        result = await runtime.processar_arquivo_excel(b"PK\x03\x04xlsx")
        assert result[0]["erro_processamento_excel"] == "excel fail"

        monkeypatch.setattr(
            file_processing.TabularIngestionEngineRuntime,
            "_parse_csv_records_in_subprocess",
            lambda self, **kwargs: {
                "ok": False,
                "error_code": "FILE_PARSE_UNSAFE",
                "error": "csv fail",
            },
        )
        result = await runtime.processar_arquivo_csv(b"x")
        assert result[0]["erro_processamento_csv"] == "csv fail"

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
        assert impl._resolve_max_upload_bytes() == 0
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

    def test_file_processing_subprocess_helpers_cover_timeout_and_failure_payloads(
        monkeypatch,
        tmp_path,
    ):
        """Cover parser subprocess helper branches without spawning real children."""
        impl = file_processing._FileProcessingImplementation

        monkeypatch.setattr(file_processing.settings, "FILE_PARSE_TIMEOUT_SECONDS", "bad", raising=False)
        monkeypatch.setattr(file_processing.settings, "FILE_PARSE_MAX_MEMORY_MB", "bad", raising=False)
        assert impl._resolve_file_parse_timeout_seconds() == 30
        assert impl._resolve_file_parse_max_memory_mb() == 0
        project_root = impl._resolve_project_root()
        assert (project_root / "Backend").exists()
        assert impl._build_file_parse_error_payload(
            prefix="erro",
            error_code="FILE_PARSE_TIMEOUT",
            detail="timed out",
        ) == {"erro": "timed out", "error_code": "FILE_PARSE_TIMEOUT"}

        class _Completed:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run_success(command, **kwargs):
            _ = kwargs
            output_index = command.index("--output") + 1
            Path(command[output_index]).write_text(
                '{"ok": true, "records": [{"sku": "A1"}]}',
                encoding="utf-8",
            )
            return _Completed()

        class _FakeNamedTempFile:
            counter = 0

            def __init__(self, suffix):
                self.name = str(tmp_path / f"tmp-{_FakeNamedTempFile.counter}{suffix}")
                _FakeNamedTempFile.counter += 1

            def __enter__(self):
                Path(self.name).write_bytes(b"")
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def write(self, payload):
                Path(self.name).write_bytes(payload)

        monkeypatch.setattr(
            file_processing.tempfile,
            "NamedTemporaryFile",
            lambda delete=False, suffix="": _FakeNamedTempFile(suffix),
        )
        monkeypatch.setattr(file_processing.subprocess, "run", fake_run_success)
        success = impl._run_tabular_parse_subprocess(
            mode="excel_ingest",
            content=b"PK\x03\x04xlsx",
            suffix=".xlsx",
        )
        assert success == {"ok": True, "records": [{"sku": "A1"}]}

        def fake_run_invalid_json(command, **kwargs):
            _ = kwargs
            output_index = command.index("--output") + 1
            Path(command[output_index]).write_text("{invalid", encoding="utf-8")
            return _Completed()

        monkeypatch.setattr(file_processing.subprocess, "run", fake_run_invalid_json)
        invalid_json_payload = impl._run_tabular_parse_subprocess(
            mode="excel_preview",
            content=b"PK\x03\x04xlsx",
            suffix=".xlsx",
            max_rows=None,
        )
        assert invalid_json_payload["error_code"] == "FILE_PARSE_UNSAFE"

        monkeypatch.setattr(
            file_processing.subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                file_processing.subprocess.TimeoutExpired(cmd="python", timeout=1)
            ),
        )
        timeout_payload = impl._run_tabular_parse_subprocess(
            mode="excel_ingest",
            content=b"PK\x03\x04xlsx",
            suffix=".xlsx",
        )
        assert timeout_payload["error_code"] == "FILE_PARSE_TIMEOUT"

        class _CompletedKilled:
            returncode = -9
            stdout = ""
            stderr = ""

        monkeypatch.setattr(file_processing.settings, "FILE_PARSE_MAX_MEMORY_MB", 64, raising=False)
        monkeypatch.setattr(file_processing.subprocess, "run", lambda *args, **kwargs: _CompletedKilled())
        oom_payload = impl._run_tabular_parse_subprocess(
            mode="excel_ingest",
            content=b"PK\x03\x04xlsx",
            suffix=".xlsx",
        )
        assert oom_payload["error_code"] == "FILE_PARSE_OOM"

        class _CompletedFailure:
            returncode = 1
            stdout = ""
            stderr = "stderr fail"

        monkeypatch.setattr(file_processing.settings, "FILE_PARSE_MAX_MEMORY_MB", 0, raising=False)
        monkeypatch.setattr(file_processing.subprocess, "run", lambda *args, **kwargs: _CompletedFailure())
        unsafe_payload = impl._run_tabular_parse_subprocess(
            mode="excel_ingest",
            content=b"PK\x03\x04xlsx",
            suffix=".xlsx",
        )
        assert unsafe_payload["error_code"] == "FILE_PARSE_UNSAFE"
        assert unsafe_payload["error"] == "stderr fail"

        def fake_run_missing_output(command, **kwargs):
            _ = kwargs
            output_index = command.index("--output") + 1
            output_path = Path(command[output_index])
            if output_path.exists():
                output_path.unlink()
            return _Completed()

        monkeypatch.setattr(file_processing.subprocess, "run", fake_run_missing_output)
        missing_output_payload = impl._run_tabular_parse_subprocess(
            mode="csv_preview",
            content=b"sku,nome\nA1,Produto",
            suffix=".csv",
        )
        assert missing_output_payload["error_code"] == "FILE_PARSE_UNSAFE"

        monkeypatch.setattr(
            file_processing.tempfile,
            "NamedTemporaryFile",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("temp fail")),
        )
        generic_failure_payload = impl._run_tabular_parse_subprocess(
            mode="csv_ingest",
            content=b"sku,nome\nA1,Produto",
            suffix=".csv",
        )
        assert generic_failure_payload["error_code"] == "FILE_PARSE_UNSAFE"
        assert generic_failure_payload["error"] == "temp fail"

        monkeypatch.setattr(
            file_processing.tempfile,
            "NamedTemporaryFile",
            lambda delete=False, suffix="": _FakeNamedTempFile(suffix),
        )
        monkeypatch.setattr(file_processing.subprocess, "run", fake_run_success)
        original_unlink = Path.unlink

        def failing_unlink(self, *args, **kwargs):
            if self.name.startswith("tmp-"):
                raise OSError("locked temp")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", failing_unlink)
        cleanup_failure_payload = impl._run_tabular_parse_subprocess(
            mode="excel_ingest",
            content=b"PK\x03\x04xlsx",
            suffix=".xlsx",
        )
        assert cleanup_failure_payload == {"ok": True, "records": [{"sku": "A1"}]}

    @pytest.mark.asyncio
    async def test_file_processing_tabular_runtime_generic_exception_and_preview_wrapper_paths(
        monkeypatch,
    ):
        """Cover generic exception branches after subprocess parsing was introduced."""
        preview_runtime = file_processing.TabularPreviewEngineRuntime()
        assert preview_runtime._detect_csv_delimiter("a|b\n1|2") == "|"

        calls = []

        def fake_runner(**kwargs):
            calls.append(kwargs)
            return {"ok": True, "headers": ["sku"], "sample_rows": [{"sku": "A1"}]}

        monkeypatch.setattr(
            file_processing._FileProcessingImplementation,
            "_run_tabular_parse_subprocess",
            staticmethod(fake_runner),
        )
        assert preview_runtime._build_excel_preview_in_subprocess(
            conteudo_arquivo=b"PK\x03\x04xlsx",
            max_rows=2,
        ) == {"ok": True, "headers": ["sku"], "sample_rows": [{"sku": "A1"}]}
        assert calls[-1]["mode"] == "excel_preview"

        ingestion_runtime = file_processing.TabularIngestionRuntime()
        monkeypatch.setattr(
            file_processing.TabularIngestionEngineRuntime,
            "_parse_excel_records_in_subprocess",
            lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("excel boom")),
        )
        monkeypatch.setattr(
            file_processing.TabularIngestionEngineRuntime,
            "_parse_csv_records_in_subprocess",
            lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("csv boom")),
        )
        assert (
            await ingestion_runtime.processar_arquivo_excel(b"PK\x03\x04xlsx")
        )[0]["erro_processamento_excel"] == "Falha ao ler arquivo Excel: excel boom"
        assert (
            await ingestion_runtime.processar_arquivo_csv(b"sku,nome\nA1,Produto")
        )[0]["erro_processamento_csv"] == "Falha ao ler arquivo CSV: csv boom"

        monkeypatch.setattr(
            file_processing.TabularPreviewEngineRuntime,
            "_build_excel_preview_in_subprocess",
            lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("preview excel boom")),
        )
        monkeypatch.setattr(
            file_processing.TabularPreviewEngineRuntime,
            "_build_csv_preview_in_subprocess",
            lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("preview csv boom")),
        )
        assert await preview_runtime.preview_arquivo_excel(b"PK\x03\x04xlsx") == {
            "error": "Falha ao ler arquivo Excel: preview excel boom"
        }
        assert await preview_runtime.preview_arquivo_csv(b"sku,nome\nA1,Produto") == {
            "error": "Falha ao ler arquivo CSV: preview csv boom"
        }


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
test_file_processing_subprocess_helpers_cover_timeout_and_failure_payloads = (
    _TopLevelFunctionSurface.test_file_processing_subprocess_helpers_cover_timeout_and_failure_payloads
)
test_file_processing_tabular_runtime_generic_exception_and_preview_wrapper_paths = (
    _TopLevelFunctionSurface.test_file_processing_tabular_runtime_generic_exception_and_preview_wrapper_paths
)
