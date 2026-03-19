"""Repository and precedence helpers for AI policy resolution."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from Backend import models
from Backend.core.config import settings


class AIPolicyRepository:
    """Persist and resolve AI policy using system -> plan -> company -> user precedence."""

    _POLICY_FIELDS = (
        "generation_default_mode",
        "enrichment_default_mode",
        "allow_user_override",
        "allow_openai",
        "allow_gemini",
        "allow_attribute_ai",
        "allow_web_llm",
        "allow_provider_fallback",
        "allow_global_learning",
        "max_recovery_attempts",
        "default_provider_preference",
        "is_active",
    )

    def __init__(self, db: Session) -> None:
        """Bind repository to the current request session."""
        self._db = db

    @staticmethod
    def source_to_label(source: str) -> str:
        """Render a stable Portuguese label for one effective source."""
        mapping = {
            "company": "Empresa",
            "plan": "Plano",
            "system": "Sistema",
            "user": "Pessoal",
        }
        return mapping.get(str(source or "").strip().lower(), "Desconhecido")

    @staticmethod
    def _normalize_mode(value: Any) -> models.AIPolicyModeEnum:
        """Normalize policy modes to one of the supported enum values."""
        normalized = str(value or "").strip().lower()
        if normalized == models.AIPolicyModeEnum.COMPLETE.value:
            return models.AIPolicyModeEnum.COMPLETE
        return models.AIPolicyModeEnum.BASIC

    @staticmethod
    def _resolve_default_provider_preference() -> models.ExternalCredentialProviderEnum | None:
        """Choose a safe default provider preference from current system configuration."""
        if str(getattr(settings, "OPENAI_API_KEY", "") or "").strip():
            return models.ExternalCredentialProviderEnum.OPENAI
        if str(getattr(settings, "GOOGLE_GEMINI_API_KEY", "") or "").strip():
            return models.ExternalCredentialProviderEnum.GOOGLE_GEMINI
        return None

    def _build_system_defaults(self) -> Dict[str, Any]:
        """Build the implicit system-level defaults used when no override exists."""
        default_mode = self._normalize_mode(getattr(settings, "PRODUCT_EXPERIENCE_DEFAULT", "basic"))
        return {
            "id": None,
            "scope_type": models.AIPolicyScopeEnum.SYSTEM,
            "source_label": self.source_to_label("system"),
            "company_identifier": None,
            "plan_id": None,
            "plan_name": None,
            "generation_default_mode": default_mode,
            "enrichment_default_mode": default_mode,
            "allow_user_override": True,
            "allow_openai": True,
            "allow_gemini": True,
            "allow_attribute_ai": True,
            "allow_web_llm": True,
            "allow_provider_fallback": True,
            "allow_global_learning": True,
            "max_recovery_attempts": 1,
            "default_provider_preference": self._resolve_default_provider_preference(),
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }

    def _derive_plan_defaults(self, *, current_user: models.User) -> Dict[str, Any] | None:
        """Derive the plan-level defaults that mirror the current product behavior."""
        plan = getattr(current_user, "plano", None)
        plan_name = str(getattr(plan, "nome", "") or "").strip()
        normalized_plan_name = plan_name.lower()

        complete_mode = current_user.is_superuser or normalized_plan_name in {
            "pro",
            "enterprise",
            "empresarial",
        }
        mode = (
            models.AIPolicyModeEnum.COMPLETE
            if complete_mode
            else models.AIPolicyModeEnum.BASIC
        )
        ai_enabled = complete_mode

        if not plan and not current_user.is_superuser:
            return None

        return {
            "id": None,
            "scope_type": models.AIPolicyScopeEnum.PLAN,
            "source_label": self.source_to_label("plan"),
            "company_identifier": None,
            "plan_id": getattr(plan, "id", None),
            "plan_name": plan_name or ("Administrador" if current_user.is_superuser else None),
            "generation_default_mode": mode,
            "enrichment_default_mode": mode,
            "allow_user_override": True,
            "allow_openai": ai_enabled,
            "allow_gemini": ai_enabled,
            "allow_attribute_ai": ai_enabled,
            "allow_web_llm": ai_enabled,
            "allow_provider_fallback": True,
            "allow_global_learning": True,
            "max_recovery_attempts": 1,
            "default_provider_preference": self._resolve_default_provider_preference(),
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }

    def _subject_filters(
        self,
        *,
        scope_type: models.AIPolicyScopeEnum,
        current_user: models.User,
        plan_id: int | None = None,
    ) -> Dict[str, Any]:
        """Build the filter dict for one policy scope query."""
        if scope_type == models.AIPolicyScopeEnum.SYSTEM:
            return {
                "scope_type": scope_type,
                "plan_id": None,
                "company_identifier": None,
                "user_id": None,
            }
        if scope_type == models.AIPolicyScopeEnum.PLAN:
            resolved_plan_id = plan_id or getattr(current_user, "plano_id", None)
            if not resolved_plan_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Informe um plano valido antes de salvar politica por plano.",
                )
            return {
                "scope_type": scope_type,
                "plan_id": resolved_plan_id,
                "company_identifier": None,
                "user_id": None,
            }
        if scope_type == models.AIPolicyScopeEnum.COMPANY:
            company_identifier = current_user.company_identifier
            if not company_identifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Informe o nome da empresa no perfil antes de salvar politica da empresa.",
                )
            return {
                "scope_type": scope_type,
                "plan_id": None,
                "company_identifier": company_identifier,
                "user_id": None,
            }
        return {
            "scope_type": models.AIPolicyScopeEnum.USER,
            "plan_id": None,
            "company_identifier": None,
            "user_id": current_user.id,
        }

    def get_config(
        self,
        *,
        scope_type: models.AIPolicyScopeEnum,
        current_user: models.User,
        plan_id: int | None = None,
    ) -> Optional[models.AIPolicyConfig]:
        """Fetch a single policy config matching scope and current subject context."""
        filters = self._subject_filters(
            scope_type=scope_type,
            current_user=current_user,
            plan_id=plan_id,
        )
        return self._db.query(models.AIPolicyConfig).filter_by(**filters).first()

    def upsert_config(
        self,
        *,
        scope_type: models.AIPolicyScopeEnum,
        current_user: models.User,
        generation_default_mode: models.AIPolicyModeEnum,
        enrichment_default_mode: models.AIPolicyModeEnum,
        allow_user_override: bool,
        allow_openai: bool,
        allow_gemini: bool,
        allow_attribute_ai: bool,
        allow_web_llm: bool,
        allow_provider_fallback: bool,
        allow_global_learning: bool,
        max_recovery_attempts: int,
        default_provider_preference: models.ExternalCredentialProviderEnum | None,
        is_active: bool,
        plan_id: int | None = None,
    ) -> models.AIPolicyConfig:
        """Create or update one policy scope entry."""
        filters = self._subject_filters(
            scope_type=scope_type,
            current_user=current_user,
            plan_id=plan_id,
        )
        config = self._db.query(models.AIPolicyConfig).filter_by(**filters).first()
        if config is None:
            config = models.AIPolicyConfig(**filters)
            self._db.add(config)

        config.generation_default_mode = self._normalize_mode(generation_default_mode)
        config.enrichment_default_mode = self._normalize_mode(enrichment_default_mode)
        config.allow_user_override = bool(allow_user_override)
        config.allow_openai = bool(allow_openai)
        config.allow_gemini = bool(allow_gemini)
        config.allow_attribute_ai = bool(allow_attribute_ai)
        config.allow_web_llm = bool(allow_web_llm)
        config.allow_provider_fallback = bool(allow_provider_fallback)
        config.allow_global_learning = bool(allow_global_learning)
        config.max_recovery_attempts = max(0, min(int(max_recovery_attempts), 10))
        config.default_provider_preference = default_provider_preference
        config.is_active = bool(is_active)
        self._db.commit()
        self._db.refresh(config)
        return config

    def delete_config(
        self,
        *,
        scope_type: models.AIPolicyScopeEnum,
        current_user: models.User,
        plan_id: int | None = None,
    ) -> bool:
        """Delete one policy scope config and return True if it existed."""
        config = self.get_config(
            scope_type=scope_type,
            current_user=current_user,
            plan_id=plan_id,
        )
        if config is None:
            return False
        self._db.delete(config)
        self._db.commit()
        return True

    def serialize_config(
        self,
        config: models.AIPolicyConfig,
        *,
        source_label: str | None = None,
        plan_name: str | None = None,
    ) -> Dict[str, Any]:
        """Serialize one stored policy config for API responses."""
        return {
            "id": config.id,
            "scope_type": config.scope_type,
            "source_label": source_label or self.source_to_label(config.scope_type.value),
            "company_identifier": config.company_identifier,
            "plan_id": config.plan_id,
            "plan_name": plan_name,
            "generation_default_mode": config.generation_default_mode,
            "enrichment_default_mode": config.enrichment_default_mode,
            "allow_user_override": config.allow_user_override,
            "allow_openai": config.allow_openai,
            "allow_gemini": config.allow_gemini,
            "allow_attribute_ai": config.allow_attribute_ai,
            "allow_web_llm": config.allow_web_llm,
            "allow_provider_fallback": config.allow_provider_fallback,
            "allow_global_learning": config.allow_global_learning,
            "max_recovery_attempts": config.max_recovery_attempts,
            "default_provider_preference": config.default_provider_preference,
            "is_active": config.is_active,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def _merge_policy_layers(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Overlay the policy fields from one layer onto another."""
        merged = {**base}
        for field_name in self._POLICY_FIELDS:
            merged[field_name] = override[field_name]
        return merged

    def _resolve_plan_layer(self, *, current_user: models.User) -> Dict[str, Any] | None:
        """Resolve the current plan layer, combining derived defaults and stored overrides."""
        base_plan_layer = self._derive_plan_defaults(current_user=current_user)
        stored_plan_config = None
        resolved_plan_id = getattr(current_user, "plano_id", None)
        if resolved_plan_id:
            stored_plan_config = self.get_config(
                scope_type=models.AIPolicyScopeEnum.PLAN,
                current_user=current_user,
                plan_id=resolved_plan_id,
            )

        if stored_plan_config is None:
            return base_plan_layer

        serialized = self.serialize_config(
            stored_plan_config,
            source_label=self.source_to_label("plan"),
            plan_name=str(getattr(getattr(current_user, "plano", None), "nome", "") or "").strip()
            or None,
        )
        if base_plan_layer is None:
            return serialized
        return self._merge_policy_layers(base_plan_layer, serialized)

    def resolve_effective_config(self, *, current_user: models.User) -> Dict[str, Any]:
        """Resolve the effective policy using system -> plan -> company -> user precedence."""
        system_config = self._build_system_defaults()
        plan_config = self._resolve_plan_layer(current_user=current_user)
        company_config_model = self.get_config(
            scope_type=models.AIPolicyScopeEnum.COMPANY,
            current_user=current_user,
        )
        company_config = (
            self.serialize_config(company_config_model, source_label=self.source_to_label("company"))
            if company_config_model
            else None
        )
        user_config_model = self.get_config(
            scope_type=models.AIPolicyScopeEnum.USER,
            current_user=current_user,
        )
        user_config = (
            self.serialize_config(user_config_model, source_label=self.source_to_label("user"))
            if user_config_model
            else None
        )

        effective = dict(system_config)
        effective_source = "system"

        for source_name, layer in (
            ("plan", plan_config),
            ("company", company_config),
            ("user", user_config),
        ):
            if layer and layer.get("is_active", True):
                effective = self._merge_policy_layers(effective, layer)
                effective_source = source_name

        effective["source"] = effective_source
        effective["source_label"] = self.source_to_label(effective_source)
        return effective

    def build_overview(self, *, current_user: models.User) -> Dict[str, Any]:
        """Build the policy overview returned to the authenticated user."""
        system_config = self._build_system_defaults()
        plan_config = self._resolve_plan_layer(current_user=current_user)
        company_config_model = self.get_config(
            scope_type=models.AIPolicyScopeEnum.COMPANY,
            current_user=current_user,
        )
        user_config_model = self.get_config(
            scope_type=models.AIPolicyScopeEnum.USER,
            current_user=current_user,
        )
        return {
            "company_identifier": current_user.company_identifier,
            "plan_id": getattr(current_user, "plano_id", None),
            "plan_name": str(getattr(getattr(current_user, "plano", None), "nome", "") or "").strip()
            or None,
            "system_config": system_config,
            "plan_config": plan_config,
            "company_config": (
                self.serialize_config(company_config_model, source_label=self.source_to_label("company"))
                if company_config_model
                else None
            ),
            "user_config": (
                self.serialize_config(user_config_model, source_label=self.source_to_label("user"))
                if user_config_model
                else None
            ),
            "effective_config": self.resolve_effective_config(current_user=current_user),
        }
