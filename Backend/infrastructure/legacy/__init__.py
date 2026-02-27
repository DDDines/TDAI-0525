"""Legacy infrastructure bridges namespace.

Avoid importing concrete bridges at package import time to prevent circular
imports and heavy side effects when only one bridge is needed.
"""

__all__: list[str] = []
