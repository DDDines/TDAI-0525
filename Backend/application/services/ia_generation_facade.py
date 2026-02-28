from __future__ import annotations

from Backend.application.services.ia_generation_service import IAGenerationService


class IAGenerationFacade(IAGenerationService):
    """Compatibility facade preserved during migration; use IAGenerationService."""
