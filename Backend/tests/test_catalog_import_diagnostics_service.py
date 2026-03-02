"""Module test catalog import diagnostics service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from pathlib import Path

from Backend.application.services.catalog_import_diagnostics_service import (
    CatalogImportDiagnosticsService,
)


class _SanitizationStub:
    """Class _SanitizationStub.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def extract_import_error_reason(item):
        """Execute extract_import_error_reason.

        This callable is documented to make behavior explicit for readers.
        """
        if isinstance(item, dict):
            return item.get("motivo_descarte") or "erro_sem_motivo"
        return "erro_sem_motivo"


class _LoggerStub:
    """Class _LoggerStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.messages = []

    def warning(self, message, *args):
        """Execute warning.

        This callable is documented to make behavior explicit for readers.
        """
        self.messages.append((message, args))


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(tmp_path: Path) -> CatalogImportDiagnosticsService:
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        return CatalogImportDiagnosticsService(
            catalog_log_dir=tmp_path / "logs",
            logger=_LoggerStub(),
            sanitization_service=_SanitizationStub(),
        )

    def test_resolve_storage_path_keeps_absolute(tmp_path):
        """Execute test_resolve_storage_path_keeps_absolute.

        This callable is documented to make behavior explicit for readers.
        """
        service = _build_service(tmp_path)
        absolute = tmp_path / "data" / "catalog.pdf"
        assert service.resolve_storage_path(absolute) == absolute

    def test_resolve_storage_path_with_backend_prefix(tmp_path):
        """Execute test_resolve_storage_path_with_backend_prefix.

        This callable is documented to make behavior explicit for readers.
        """
        service = _build_service(tmp_path)
        resolved = service.resolve_storage_path("Backend/uploads/catalogs/file.pdf")
    
        assert resolved.parts[-4:] == ("Backend", "uploads", "catalogs", "file.pdf")

    def test_write_catalog_import_report_persists_json(tmp_path):
        """Execute test_write_catalog_import_report_persists_json.

        This callable is documented to make behavior explicit for readers.
        """
        service = _build_service(tmp_path)
        report_path = service.write_catalog_import_report(
            file_id=321,
            status="DONE",
            created_count=10,
            updated_count=2,
            errors=[
                {"motivo_descarte": "linha ruim 1"},
                {"motivo_descarte": "linha ruim 2"},
                {"motivo_descarte": "linha ruim 1"},
            ],
            pages_processed=3,
            pages_total=3,
            ext=".pdf",
        )
    
        assert report_path is not None
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert '"file_id": 321' in content
        assert '"status": "DONE"' in content
        assert "linha ruim 1" in content

_build_service = _TopLevelFunctionSurface._build_service
test_resolve_storage_path_keeps_absolute = _TopLevelFunctionSurface.test_resolve_storage_path_keeps_absolute
test_resolve_storage_path_with_backend_prefix = _TopLevelFunctionSurface.test_resolve_storage_path_with_backend_prefix
test_write_catalog_import_report_persists_json = _TopLevelFunctionSurface.test_write_catalog_import_report_persists_json






