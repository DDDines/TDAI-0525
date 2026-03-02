"""Module test file processing preview dispatch runtime.

Contains backend logic related to test file processing preview dispatch runtime and documents its role in the OOP architecture.
"""

import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_preview_dispatch_runtime_uses_injected_factory():
        """Run test preview dispatch runtime uses injected factory in this workflow."""
        called = {}
    
        class FakeExtractor:
            """Represent fake extractor and centralize responsibilities for this module."""
            async def extract(self, **kwargs):
                """Run extract in this workflow."""
                called["extract"] = kwargs
                return {"ok": True}
    
        class FakeFactory:
            """Represent fake factory and centralize responsibilities for this module."""
            def __init__(self):
                """Initialize collaborators and configuration required by this component."""
                self.received_ext = None
    
            def get_extractor(self, ext_norm):
                """Return extractor for this workflow."""
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
        """Run test preview dispatch runtime raises for unsupported extension in this workflow."""
        runtime = file_processing.PreviewDispatchRuntime()
    
        with pytest.raises(ValueError):
            await runtime.gerar_preview(
                conteudo_arquivo=b"abc",
                ext=".bin",
                max_rows=5,
            )

test_preview_dispatch_runtime_uses_injected_factory = _TopLevelFunctionSurface.test_preview_dispatch_runtime_uses_injected_factory
test_preview_dispatch_runtime_raises_for_unsupported_extension = _TopLevelFunctionSurface.test_preview_dispatch_runtime_raises_for_unsupported_extension



