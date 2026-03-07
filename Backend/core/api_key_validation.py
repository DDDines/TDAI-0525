"""Helpers for validating external provider API keys before runtime use."""

from __future__ import annotations

from typing import Any


def normalize_optional_secret(value: Any) -> str | None:
    """Normalize arbitrary secret-like values into compact strings or ``None``."""
    text = str(value or "").strip()
    return text or None


def looks_like_openai_api_key(value: Any) -> bool:
    """Accept only OpenAI-style secret keys and ignore malformed saved values."""
    text = normalize_optional_secret(value)
    if not text:
        return False
    return text.startswith("sk-") and len(text) >= 20

