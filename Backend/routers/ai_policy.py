"""Endpoints for persisted AI policy layers and effective resolution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.ai_policy_repository import AIPolicyRepository

from . import auth_utils

router = APIRouter(
    prefix="/ai-policy",
    tags=["ai-policy"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class _AIPolicyEndpointHelpers:
    """Static permission helpers shared across AI policy endpoints."""

    @staticmethod
    def _ensure_elevated_scope_allowed(
        *,
        scope_type: models.AIPolicyScopeEnum,
        current_user: models.User,
    ) -> None:
        """Restrict system, plan and company policy changes to admins."""
        if scope_type == models.AIPolicyScopeEnum.USER:
            return
        role_name = str(getattr(getattr(current_user, "role", None), "name", "") or "").strip().lower()
        if current_user.is_superuser or role_name == "admin":
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente administradores podem gerenciar politicas elevadas de IA.",
        )


_ensure_elevated_scope_allowed = _AIPolicyEndpointHelpers._ensure_elevated_scope_allowed


@router.get("/overview", response_model=schemas.AIPolicyOverviewResponse)
def read_ai_policy_overview(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Return all visible AI policy layers plus the effective resolved config."""
    repository = AIPolicyRepository(session)
    return repository.build_overview(current_user=current_user)


@router.put("", response_model=schemas.AIPolicyConfigResponse)
def upsert_ai_policy(
    payload: schemas.AIPolicyConfigUpsert,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Create or update one AI policy scope."""
    _ensure_elevated_scope_allowed(scope_type=payload.scope_type, current_user=current_user)
    repository = AIPolicyRepository(session)
    config = repository.upsert_config(
        scope_type=payload.scope_type,
        current_user=current_user,
        generation_default_mode=payload.generation_default_mode,
        enrichment_default_mode=payload.enrichment_default_mode,
        allow_user_override=payload.allow_user_override,
        allow_openai=payload.allow_openai,
        allow_gemini=payload.allow_gemini,
        allow_attribute_ai=payload.allow_attribute_ai,
        allow_web_llm=payload.allow_web_llm,
        allow_provider_fallback=payload.allow_provider_fallback,
        allow_global_learning=payload.allow_global_learning,
        max_recovery_attempts=payload.max_recovery_attempts,
        default_provider_preference=payload.default_provider_preference,
        is_active=payload.is_active,
        plan_id=payload.plan_id,
    )
    return repository.serialize_config(config)


@router.delete("/{scope_type}", response_model=schemas.Msg)
def delete_ai_policy(
    scope_type: models.AIPolicyScopeEnum,
    plan_id: int | None = Query(None),
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Delete one AI policy scope config and fall back to the next precedence layer."""
    _ensure_elevated_scope_allowed(scope_type=scope_type, current_user=current_user)
    repository = AIPolicyRepository(session)
    deleted = repository.delete_config(
        scope_type=scope_type,
        current_user=current_user,
        plan_id=plan_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Politica de IA nao encontrada.",
        )
    return schemas.Msg(msg="Politica de IA removida com sucesso.")
