from __future__ import annotations

import warnings
from typing import Any

from Backend.core.legacy_guard import assert_legacy_usage_allowed


class _DeprecatedLegacyServiceProxy:
    def __init__(
        self,
        *,
        service: Any,
        qualified_name: str,
        removal_date: str,
    ) -> None:
        self._service = service
        self._qualified_name = qualified_name
        self._removal_date = removal_date
        self._warned = False

    def _warn_once(self) -> None:
        if self._warned:
            return
        warnings.warn(
            (
                f"{self._qualified_name} is deprecated and will be removed after "
                f"{self._removal_date}."
            ),
            DeprecationWarning,
            stacklevel=3,
        )
        self._warned = True

    def __getattr__(self, attr_name: str) -> Any:
        assert_legacy_usage_allowed(self._qualified_name)
        self._warn_once()
        return getattr(self._service, attr_name)


def deprecated_legacy_service_proxy(
    service: Any,
    *,
    qualified_name: str,
    removal_date: str = "2026-04-30",
) -> Any:
    return _DeprecatedLegacyServiceProxy(
        service=service,
        qualified_name=qualified_name,
        removal_date=removal_date,
    )
