"""Repository and precedence helpers for basic-mode generation templates."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)


class BasicGenerationTemplateRepository:
    """Persist and resolve basic-mode templates using user > company > system precedence."""

    _SYSTEM_DEFAULTS = {
        "title_template": BasicContentGenerationService._DEFAULT_TITLE_TEMPLATE,
        "description_template": BasicContentGenerationService._DEFAULT_DESCRIPTION_TEMPLATE,
    }

    def __init__(self, db: Session) -> None:
        """Bind the repository to the current request session."""
        self._db = db

    @classmethod
    def system_defaults(cls) -> Dict[str, str]:
        """Return the built-in templates used when no override exists."""
        return dict(cls._SYSTEM_DEFAULTS)

    @staticmethod
    def source_to_label(source: str) -> str:
        """Render a stable Portuguese label for one template source."""
        mapping = {
            "company": "Empresa",
            "system": "Sistema",
            "user": "Pessoal",
        }
        return mapping.get(str(source or "").strip().lower(), "Desconhecido")

    @classmethod
    def _normalize_template(cls, value: Any, *, fallback: str) -> str:
        """Normalize free-text templates into a safe persisted representation."""
        text = str(value or "").replace("\r\n", "\n").strip()
        if not text:
            return fallback
        return text[:2000]

    def _subject_filters(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        current_user: models.User,
    ) -> Dict[str, Any]:
        """Build the subject filter used to fetch or persist one template scope."""
        if scope_type == models.ExternalCredentialScopeEnum.USER:
            return {
                "scope_type": scope_type,
                "user_id": current_user.id,
                "company_identifier": None,
            }
        company_identifier = current_user.company_identifier
        if not company_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o nome da empresa no perfil antes de salvar templates da empresa.",
            )
        return {
            "scope_type": scope_type,
            "user_id": None,
            "company_identifier": company_identifier,
        }

    def get_config(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        current_user: models.User,
    ) -> Optional[models.BasicGenerationTemplateConfig]:
        """Fetch one stored template config for the given scope."""
        filters = self._subject_filters(scope_type=scope_type, current_user=current_user)
        return (
            self._db.query(models.BasicGenerationTemplateConfig)
            .filter_by(**filters)
            .first()
        )

    def upsert_config(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        current_user: models.User,
        title_template: Optional[str],
        description_template: Optional[str],
        is_active: bool,
    ) -> models.BasicGenerationTemplateConfig:
        """Create or update one stored template config."""
        filters = self._subject_filters(scope_type=scope_type, current_user=current_user)
        config = (
            self._db.query(models.BasicGenerationTemplateConfig)
            .filter_by(**filters)
            .first()
        )
        if config is None:
            config = models.BasicGenerationTemplateConfig(**filters)
            self._db.add(config)

        defaults = self.system_defaults()
        config.title_template = self._normalize_template(
            title_template,
            fallback=defaults["title_template"],
        )
        config.description_template = self._normalize_template(
            description_template,
            fallback=defaults["description_template"],
        )
        config.is_active = bool(is_active)
        self._db.commit()
        self._db.refresh(config)
        return config

    def delete_config(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        current_user: models.User,
    ) -> bool:
        """Delete one stored template config and return whether it existed."""
        config = self.get_config(scope_type=scope_type, current_user=current_user)
        if config is None:
            return False
        self._db.delete(config)
        self._db.commit()
        return True

    def serialize_config(
        self,
        config: models.BasicGenerationTemplateConfig,
    ) -> Dict[str, Any]:
        """Serialize one stored config for API responses."""
        source = (
            "company"
            if config.scope_type == models.ExternalCredentialScopeEnum.COMPANY
            else "user"
        )
        return {
            "id": config.id,
            "scope_type": config.scope_type,
            "title_template": config.title_template,
            "description_template": config.description_template,
            "is_active": config.is_active,
            "source_label": self.source_to_label(source),
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def resolve_effective_config(
        self,
        *,
        current_user: models.User,
    ) -> Dict[str, Any]:
        """Resolve the effective templates using user > company > system precedence."""
        defaults = self.system_defaults()
        user_config = self.get_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            current_user=current_user,
        )
        if user_config and user_config.is_active:
            return {
                "source": "user",
                "source_label": self.source_to_label("user"),
                "title_template": self._normalize_template(
                    user_config.title_template,
                    fallback=defaults["title_template"],
                ),
                "description_template": self._normalize_template(
                    user_config.description_template,
                    fallback=defaults["description_template"],
                ),
                "is_custom": True,
            }

        company_identifier = current_user.company_identifier
        if company_identifier:
            company_config = self.get_config(
                scope_type=models.ExternalCredentialScopeEnum.COMPANY,
                current_user=current_user,
            )
            if company_config and company_config.is_active:
                return {
                    "source": "company",
                    "source_label": self.source_to_label("company"),
                    "title_template": self._normalize_template(
                        company_config.title_template,
                        fallback=defaults["title_template"],
                    ),
                    "description_template": self._normalize_template(
                        company_config.description_template,
                        fallback=defaults["description_template"],
                    ),
                    "is_custom": True,
                }

        return {
            "source": "system",
            "source_label": self.source_to_label("system"),
            "title_template": defaults["title_template"],
            "description_template": defaults["description_template"],
            "is_custom": False,
        }

    def build_overview(self, *, current_user: models.User) -> Dict[str, Any]:
        """Build the basic template overview shown in the settings page."""
        company_config = None
        if current_user.company_identifier:
            company_config = self.get_config(
                scope_type=models.ExternalCredentialScopeEnum.COMPANY,
                current_user=current_user,
            )
        user_config = self.get_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            current_user=current_user,
        )
        defaults = self.system_defaults()
        return {
            "company_identifier": current_user.company_identifier,
            "company_config": self.serialize_config(company_config) if company_config else None,
            "user_config": self.serialize_config(user_config) if user_config else None,
            "effective_config": self.resolve_effective_config(current_user=current_user),
            "system_defaults": defaults,
        }
