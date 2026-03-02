"""Module test file processing preview dispatch runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_preview_dispatch_runtime_uses_injected_factory():
        """Execute test_preview_dispatch_runtime_uses_injected_factory.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        class FakeExtractor:
            """Class FakeExtractor.

            Encapsulates one responsibility in the backend architecture.
            """
            async def extract(self, **kwargs):
                """Execute extract.

                This callable is documented to make behavior explicit for readers.
                """
                called["extract"] = kwargs
                return {"ok": True}
    
        class FakeFactory:
            """Class FakeFactory.

            Encapsulates one responsibility in the backend architecture.
            """
            def __init__(self):
                """Execute __init__.

                This callable is documented to make behavior explicit for readers.
                """
                self.received_ext = None
    
            def get_extractor(self, ext_norm):
                """Execute get_extractor.

                This callable is documented to make behavior explicit for readers.
                """
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
        """Execute test_preview_dispatch_runtime_raises_for_unsupported_extension.

        This callable is documented to make behavior explicit for readers.
        """
        runtime = file_processing.PreviewDispatchRuntime()
    
        with pytest.raises(ValueError):
            await runtime.gerar_preview(
                conteudo_arquivo=b"abc",
                ext=".bin",
                max_rows=5,
            )

test_preview_dispatch_runtime_uses_injected_factory = _TopLevelFunctionSurface.test_preview_dispatch_runtime_uses_injected_factory
test_preview_dispatch_runtime_raises_for_unsupported_extension = _TopLevelFunctionSurface.test_preview_dispatch_runtime_raises_for_unsupported_extension



