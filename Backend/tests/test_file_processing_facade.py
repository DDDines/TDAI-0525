from __future__ import annotations

import pytest

from Backend.application.services.file_processing_facade import FileProcessingFacade


class _LegacyStub:
    def __init__(self) -> None:
        self.calls = []

    async def save_uploaded_catalog(self, *args, **kwargs):
        self.calls.append(("save_uploaded_catalog", args, kwargs))
        return {"ok": True}

    def delete_catalog_file(self, *args, **kwargs):
        self.calls.append(("delete_catalog_file", args, kwargs))
        return None


class _TopLevelFunctionSurface:

    @pytest.mark.asyncio
    async def test_file_processing_facade_delegates_async_calls():
        legacy = _LegacyStub()
        facade = FileProcessingFacade(port=legacy)
    
        result = await facade.save_uploaded_catalog("db", "file")
    
        assert result == {"ok": True}
        assert legacy.calls[0][0] == "save_uploaded_catalog"
        assert legacy.calls[0][1] == ("db", "file")

    def test_file_processing_facade_delegates_sync_calls():
        legacy = _LegacyStub()
        facade = FileProcessingFacade(port=legacy)
    
        facade.delete_catalog_file("abc.pdf")
    
        assert legacy.calls[0][0] == "delete_catalog_file"
        assert legacy.calls[0][1] == ("abc.pdf",)

    def test_file_processing_facade_does_not_expose_dynamic_attribute_fallback():
        legacy = _LegacyStub()
        facade = FileProcessingFacade(port=legacy)
    
        with pytest.raises(AttributeError):
            _ = facade.constant_value

test_file_processing_facade_delegates_async_calls = _TopLevelFunctionSurface.test_file_processing_facade_delegates_async_calls
test_file_processing_facade_delegates_sync_calls = _TopLevelFunctionSurface.test_file_processing_facade_delegates_sync_calls
test_file_processing_facade_does_not_expose_dynamic_attribute_fallback = _TopLevelFunctionSurface.test_file_processing_facade_does_not_expose_dynamic_attribute_fallback




