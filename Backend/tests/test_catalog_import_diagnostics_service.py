"""Module test catalog import diagnostics service.

Contains backend logic related to test catalog import diagnostics service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from pathlib import Path

from Backend.application.services.catalog_import_diagnostics_service import (
    CatalogImportDiagnosticsService,
)


class _SanitizationStub:
    """Represent sanitization stub and centralize responsibilities for this module."""
    @staticmethod
    def extract_import_error_reason(item):
        """Extract import error reason for this workflow."""
        if isinstance(item, dict):
            return item.get("motivo_descarte") or "erro_sem_motivo"
        return "erro_sem_motivo"


class _LoggerStub:
    """Represent logger stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.messages = []

    def warning(self, message, *args):
        """Run warning in this workflow."""
        self.messages.append((message, args))


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(tmp_path: Path) -> CatalogImportDiagnosticsService:
        """Run build service in this workflow."""
        return CatalogImportDiagnosticsService(
            catalog_log_dir=tmp_path / "logs",
            logger=_LoggerStub(),
            sanitization_service=_SanitizationStub(),
        )

    def test_resolve_storage_path_keeps_absolute(tmp_path):
        """Run test resolve storage path keeps absolute in this workflow."""
        service = _build_service(tmp_path)
        absolute = tmp_path / "data" / "catalog.pdf"
        assert service.resolve_storage_path(absolute) == absolute

    def test_resolve_storage_path_with_backend_prefix(tmp_path):
        """Run test resolve storage path with backend prefix in this workflow."""
        service = _build_service(tmp_path)
        resolved = service.resolve_storage_path("Backend/uploads/catalogs/file.pdf")
    
        assert resolved.parts[-4:] == ("Backend", "uploads", "catalogs", "file.pdf")

    def test_write_catalog_import_report_persists_json(tmp_path):
        """Run test write catalog import report persists json in this workflow."""
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






