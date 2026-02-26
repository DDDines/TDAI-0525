from __future__ import annotations

import pytest

from Backend.application.services.file_processing_facade import FileProcessingFacade


class _LegacyStub:
    def __init__(self) -> None:
        self.calls = []
        self.constant_value = 123

    async def save_uploaded_catalog(self, *args, **kwargs):
        self.calls.append(("save_uploaded_catalog", args, kwargs))
        return {"ok": True}

    def delete_catalog_file(self, *args, **kwargs):
        self.calls.append(("delete_catalog_file", args, kwargs))
        return None


@pytest.mark.asyncio
async def test_file_processing_facade_delegates_async_calls():
    legacy = _LegacyStub()
    facade = FileProcessingFacade(legacy_module=legacy)

    result = await facade.save_uploaded_catalog("db", "file")

    assert result == {"ok": True}
    assert legacy.calls[0][0] == "save_uploaded_catalog"
    assert legacy.calls[0][1] == ("db", "file")


def test_file_processing_facade_delegates_sync_calls():
    legacy = _LegacyStub()
    facade = FileProcessingFacade(legacy_module=legacy)

    facade.delete_catalog_file("abc.pdf")

    assert legacy.calls[0][0] == "delete_catalog_file"
    assert legacy.calls[0][1] == ("abc.pdf",)


def test_file_processing_facade_keeps_legacy_attribute_fallback():
    legacy = _LegacyStub()
    facade = FileProcessingFacade(legacy_module=legacy)

    assert facade.constant_value == 123

