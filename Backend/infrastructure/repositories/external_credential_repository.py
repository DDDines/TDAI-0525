"""Repository and resolution helpers for external API credentials."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from Backend import models


class ExternalCredentialRepository:
    """Persist and resolve client-managed external credentials."""

    _SYSTEM_CONFIG_MAP = {
        models.ExternalCredentialProviderEnum.OPENAI: {
            "secret_attr": "OPENAI_API_KEY",
            "description": "Credencial global do sistema",
        },
        models.ExternalCredentialProviderEnum.GOOGLE_GEMINI: {
            "secret_attr": "GOOGLE_GEMINI_API_KEY",
            "description": "Credencial global do sistema",
        },
        models.ExternalCredentialProviderEnum.GOOGLE_CSE: {
            "secret_attr": "GOOGLE_CSE_API_KEY",
            "description": "Credencial global do sistema",
            "config_builder": lambda settings: {
                "search_engine_id": getattr(settings, "GOOGLE_CSE_ID", None),
            },
        },
    }

    def __init__(self, db: Session) -> None:
        """Bind repository to the current request session."""
        self._db = db

    @staticmethod
    def mask_secret(secret_value: Optional[str]) -> Optional[str]:
        """Mask a secret value before returning it to the frontend."""
        raw = str(secret_value or "").strip()
        if not raw:
            return None
        if len(raw) <= 8:
            return "*" * len(raw)
        return f"{raw[:4]}{'*' * max(4, len(raw) - 8)}{raw[-4:]}"

    @staticmethod
    def source_to_label(source: str) -> str:
        """Render a stable Portuguese label for one effective source."""
        mapping = {
            "company": "Empresa",
            "none": "Nao configurado",
            "system": "Sistema",
            "user": "Pessoal",
        }
        return mapping.get(str(source or "").strip().lower(), "Desconhecido")

    @staticmethod
    def _provider_description(provider: models.ExternalCredentialProviderEnum) -> str:
        """Return a human-readable display name for the given credential provider."""
        labels = {
            models.ExternalCredentialProviderEnum.OPENAI: "OpenAI",
            models.ExternalCredentialProviderEnum.GOOGLE_GEMINI: "Google Gemini",
            models.ExternalCredentialProviderEnum.GOOGLE_CSE: "Google CSE",
        }
        return labels.get(provider, str(provider.value))

    def _subject_filters(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        provider: models.ExternalCredentialProviderEnum,
        current_user: models.User,
    ) -> Dict[str, Any]:
        """Build the filter dict for a user or company credential query."""
        if scope_type == models.ExternalCredentialScopeEnum.USER:
            return {
                "scope_type": scope_type,
                "provider": provider,
                "user_id": current_user.id,
                "company_identifier": None,
            }
        company_identifier = current_user.company_identifier
        if not company_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o nome da empresa no perfil antes de salvar credenciais da empresa.",
            )
        return {
            "scope_type": scope_type,
            "provider": provider,
            "user_id": None,
            "company_identifier": company_identifier,
        }

    def get_config(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        provider: models.ExternalCredentialProviderEnum,
        current_user: models.User,
    ) -> Optional[models.ExternalCredentialConfig]:
        """Fetch a single credential config matching scope, provider and user context."""
        filters = self._subject_filters(
            scope_type=scope_type,
            provider=provider,
            current_user=current_user,
        )
        return (
            self._db.query(models.ExternalCredentialConfig)
            .filter_by(**filters)
            .first()
        )

    def list_company_configs(self, *, current_user: models.User) -> List[models.ExternalCredentialConfig]:
        """List all company-scoped credential configs for the current user's company."""
        company_identifier = current_user.company_identifier
        if not company_identifier:
            return []
        return (
            self._db.query(models.ExternalCredentialConfig)
            .filter(
                models.ExternalCredentialConfig.scope_type == models.ExternalCredentialScopeEnum.COMPANY,
                models.ExternalCredentialConfig.company_identifier == company_identifier,
            )
            .order_by(models.ExternalCredentialConfig.provider.asc())
            .all()
        )

    def list_user_configs(self, *, current_user: models.User) -> List[models.ExternalCredentialConfig]:
        """List all user-scoped credential configs for the current user."""
        return (
            self._db.query(models.ExternalCredentialConfig)
            .filter(
                models.ExternalCredentialConfig.scope_type == models.ExternalCredentialScopeEnum.USER,
                models.ExternalCredentialConfig.user_id == current_user.id,
            )
            .order_by(models.ExternalCredentialConfig.provider.asc())
            .all()
        )

    def upsert_config(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        provider: models.ExternalCredentialProviderEnum,
        current_user: models.User,
        secret_value: Optional[str],
        config_json: Optional[Dict[str, Any]],
        description: Optional[str],
        is_active: bool,
    ) -> models.ExternalCredentialConfig:
        """Create or update a credential config, persisting all provided field values."""
        filters = self._subject_filters(
            scope_type=scope_type,
            provider=provider,
            current_user=current_user,
        )
        config = (
            self._db.query(models.ExternalCredentialConfig)
            .filter_by(**filters)
            .first()
        )
        if config is None:
            config = models.ExternalCredentialConfig(**filters)
            self._db.add(config)
        if secret_value is not None:
            config.secret_value = str(secret_value or "").strip() or None
        config.config_json = config_json or None
        config.description = str(description or "").strip() or None
        config.is_active = bool(is_active)
        self._db.commit()
        self._db.refresh(config)
        return config

    def delete_config(
        self,
        *,
        scope_type: models.ExternalCredentialScopeEnum,
        provider: models.ExternalCredentialProviderEnum,
        current_user: models.User,
    ) -> bool:
        """Delete a stored credential config and return True if it existed."""
        config = self.get_config(
            scope_type=scope_type,
            provider=provider,
            current_user=current_user,
        )
        if config is None:
            return False
        self._db.delete(config)
        self._db.commit()
        return True

    def serialize_config(
        self,
        config: models.ExternalCredentialConfig,
    ) -> Dict[str, Any]:
        """Serialize one credential entry for API responses."""
        source_label = (
            "Empresa"
            if config.scope_type == models.ExternalCredentialScopeEnum.COMPANY
            else "Pessoal"
        )
        return {
            "id": config.id,
            "scope_type": config.scope_type,
            "provider": config.provider,
            "secret_value": None,
            "secret_masked": self.mask_secret(config.secret_value),
            "config_json": config.config_json,
            "description": config.description,
            "is_active": config.is_active,
            "source_label": source_label,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def _resolve_system_source(
        self,
        *,
        provider: models.ExternalCredentialProviderEnum,
        settings: Any,
    ) -> Dict[str, Any]:
        """Build the system-level credential source entry from application settings."""
        system_config = self._SYSTEM_CONFIG_MAP.get(provider, {})
        secret_attr = system_config.get("secret_attr")
        secret_value = str(getattr(settings, secret_attr, "") or "").strip() if secret_attr else ""
        config_builder = system_config.get("config_builder")
        config_json = config_builder(settings) if callable(config_builder) else None
        configured = bool(secret_value) and (
            provider != models.ExternalCredentialProviderEnum.GOOGLE_CSE
            or bool((config_json or {}).get("search_engine_id"))
        )
        return {
            "provider": provider,
            "source": "system",
            "source_label": self.source_to_label("system"),
            "configured": configured,
            "description": system_config.get("description"),
            "company_identifier": None,
            "has_secret": bool(secret_value),
            "secret_value": secret_value or None,
            "config_json": config_json or None,
        }

    def resolve_effective_source(
        self,
        *,
        provider: models.ExternalCredentialProviderEnum,
        current_user: models.User,
        settings: Any,
    ) -> Dict[str, Any]:
        """Resolve the effective credential using user > company > system precedence."""
        user_config = self.get_config(
            scope_type=models.ExternalCredentialScopeEnum.USER,
            provider=provider,
            current_user=current_user,
        )
        if user_config and user_config.is_active and (
            user_config.secret_value or user_config.config_json
        ):
            return {
                "provider": provider,
                "source": "user",
                "source_label": self.source_to_label("user"),
                "configured": True,
                "description": user_config.description,
                "company_identifier": None,
                "has_secret": bool(user_config.secret_value),
                "secret_value": user_config.secret_value,
                "config_json": user_config.config_json or None,
            }

        legacy_secret = None
        if provider == models.ExternalCredentialProviderEnum.OPENAI:
            legacy_secret = getattr(current_user, "chave_openai_pessoal", None)
        elif provider == models.ExternalCredentialProviderEnum.GOOGLE_GEMINI:
            legacy_secret = getattr(current_user, "chave_google_gemini_pessoal", None)
        legacy_secret = str(legacy_secret or "").strip() or None
        if legacy_secret:
            return {
                "provider": provider,
                "source": "user",
                "source_label": self.source_to_label("user"),
                "configured": True,
                "description": "Credencial pessoal legada do usuario",
                "company_identifier": None,
                "has_secret": True,
                "secret_value": legacy_secret,
                "config_json": None,
            }

        company_identifier = current_user.company_identifier
        company_config = None
        if company_identifier:
            company_config = self.get_config(
                scope_type=models.ExternalCredentialScopeEnum.COMPANY,
                provider=provider,
                current_user=current_user,
            )
        if company_config and company_config.is_active and (
            company_config.secret_value or company_config.config_json
        ):
            return {
                "provider": provider,
                "source": "company",
                "source_label": self.source_to_label("company"),
                "configured": True,
                "description": company_config.description,
                "company_identifier": company_identifier,
                "has_secret": bool(company_config.secret_value),
                "secret_value": company_config.secret_value,
                "config_json": company_config.config_json or None,
            }

        system_source = self._resolve_system_source(provider=provider, settings=settings)
        if system_source["configured"]:
            return system_source
        return {
            "provider": provider,
            "source": "none",
            "source_label": self.source_to_label("none"),
            "configured": False,
            "description": f"{self._provider_description(provider)} nao configurado",
            "company_identifier": company_identifier,
            "has_secret": False,
            "secret_value": None,
            "config_json": None,
        }

    def build_overview(self, *, current_user: models.User, settings: Any) -> Dict[str, Any]:
        """Build a credential overview for settings UI."""
        providers = list(models.ExternalCredentialProviderEnum)
        return {
            "company_identifier": current_user.company_identifier,
            "company_credentials": [
                self.serialize_config(config) for config in self.list_company_configs(current_user=current_user)
            ],
            "user_credentials": [
                self.serialize_config(config) for config in self.list_user_configs(current_user=current_user)
            ],
            "effective_sources": [
                {
                    key: value
                    for key, value in self.resolve_effective_source(
                        provider=provider,
                        current_user=current_user,
                        settings=settings,
                    ).items()
                    if key != "secret_value"
                }
                for provider in providers
            ],
        }

    def validate_payload(
        self,
        *,
        provider: models.ExternalCredentialProviderEnum,
        secret_value: Optional[str],
        config_json: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Perform local validation of provider-specific credential payloads."""
        secret = str(secret_value or "").strip()
        config_json = config_json or {}
        errors: List[str] = []
        if provider == models.ExternalCredentialProviderEnum.OPENAI and not secret:
            errors.append("Informe a API key da OpenAI.")
        elif provider == models.ExternalCredentialProviderEnum.GOOGLE_GEMINI and not secret:
            errors.append("Informe a API key do Google Gemini.")
        elif provider == models.ExternalCredentialProviderEnum.GOOGLE_CSE:
            if not secret:
                errors.append("Informe a API key do Google CSE.")
            if not str(config_json.get("search_engine_id") or "").strip():
                errors.append("Informe o Search Engine ID do Google CSE.")
        return {
            "provider": provider,
            "valid": len(errors) == 0,
            "errors": errors,
        }
