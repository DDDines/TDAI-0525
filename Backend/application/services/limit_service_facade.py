from __future__ import annotations

from Backend.application.services.limit_service import LimitService


class LimitServiceFacade(LimitService):
    """Compatibility facade preserved during migration; use LimitService."""
