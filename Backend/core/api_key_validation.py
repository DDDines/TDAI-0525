"""Helpers for validating external provider API keys before runtime use."""

from __future__ import annotations

from typing import Any


class ApiKeyValidationRuntime:
    """Centralize lightweight provider key validation helpers for runtime usage."""

    @staticmethod
    def normalize_optional_secret(value: Any) -> str | None:
        """Normalize arbitrary secret-like values into compact strings or ``None``."""
        text = str(value or "").strip()
        return text or None

    @classmethod
    def looks_like_openai_api_key(cls, value: Any) -> bool:
        """Accept only OpenAI-style secret keys and ignore malformed saved values."""
        text = cls.normalize_optional_secret(value)
        if not text:
            return False
        return text.startswith("sk-") and len(text) >= 20


normalize_optional_secret = ApiKeyValidationRuntime.normalize_optional_secret
looks_like_openai_api_key = ApiKeyValidationRuntime.looks_like_openai_api_key
