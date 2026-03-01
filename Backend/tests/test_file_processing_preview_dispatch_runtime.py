import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    @pytest.mark.asyncio
    async def test_preview_dispatch_runtime_uses_injected_factory():
        called = {}
    
        class FakeExtractor:
            async def extract(self, **kwargs):
                called["extract"] = kwargs
                return {"ok": True}
    
        class FakeFactory:
            def __init__(self):
                self.received_ext = None
    
            def get_extractor(self, ext_norm):
                self.received_ext = ext_norm
                return FakeExtractor()
    
        factory = FakeFactory()
        runtime = file_processing.PreviewDispatchRuntime(extractor_factory=factory)
    
        result = await runtime.gerar_preview(
            conteudo_arquivo=b"abc",
            ext=".PDF",
            max_rows=7,
        )
    
        assert result == {"ok": True}
        assert factory.received_ext == ".pdf"
        assert called["extract"]["ext"] == ".pdf"
        assert called["extract"]["max_rows"] == 7

    @pytest.mark.asyncio
    async def test_preview_dispatch_runtime_raises_for_unsupported_extension():
        runtime = file_processing.PreviewDispatchRuntime()
    
        with pytest.raises(ValueError):
            await runtime.gerar_preview(
                conteudo_arquivo=b"abc",
                ext=".bin",
                max_rows=5,
            )

test_preview_dispatch_runtime_uses_injected_factory = _TopLevelFunctionSurface.test_preview_dispatch_runtime_uses_injected_factory
test_preview_dispatch_runtime_raises_for_unsupported_extension = _TopLevelFunctionSurface.test_preview_dispatch_runtime_raises_for_unsupported_extension



