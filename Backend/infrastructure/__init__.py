"""Infrastructure package namespace.

Keep this module import-light to avoid eager loading of legacy bridges during
package initialization (which can create circular imports in tests/runtime).
"""

__all__: list[str] = []
