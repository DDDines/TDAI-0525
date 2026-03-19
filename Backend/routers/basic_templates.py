"""Endpoints for persisted basic-mode title and description templates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.basic_generation_template_repository import (
    BasicGenerationTemplateRepository,
)

from . import auth_utils

router = APIRouter(
    prefix="/templates-basicos",
    tags=["templates-basicos"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class _BasicTemplateEndpointHelpers:
    """Static helpers shared across basic template endpoints."""

    @staticmethod
    def _ensure_company_scope_allowed(current_user: models.User) -> None:
        """Restrict company-scoped template changes to admins/owners."""
        role_name = str(getattr(getattr(current_user, "role", None), "name", "") or "").strip().lower()
        if current_user.is_superuser or role_name == "admin":
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente administradores podem gerenciar templates da empresa.",
        )


_ensure_company_scope_allowed = _BasicTemplateEndpointHelpers._ensure_company_scope_allowed


@router.get("/overview", response_model=schemas.BasicGenerationTemplateOverviewResponse)
def read_basic_generation_templates_overview(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Return system defaults, stored configs and the effective resolved templates."""
    repository = BasicGenerationTemplateRepository(session)
    return repository.build_overview(current_user=current_user)


@router.put("", response_model=schemas.BasicGenerationTemplateConfigResponse)
def upsert_basic_generation_templates(
    payload: schemas.BasicGenerationTemplateConfigUpsert,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Create or update one scoped basic-mode template config."""
    if payload.scope_type == models.ExternalCredentialScopeEnum.COMPANY:
        _ensure_company_scope_allowed(current_user)

    repository = BasicGenerationTemplateRepository(session)
    config = repository.upsert_config(
        scope_type=payload.scope_type,
        current_user=current_user,
        title_template=payload.title_template,
        description_template=payload.description_template,
        is_active=payload.is_active,
    )
    return repository.serialize_config(config)


@router.delete("/{scope_type}", response_model=schemas.Msg)
def delete_basic_generation_templates(
    scope_type: models.ExternalCredentialScopeEnum,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Delete one scoped basic-mode template config and fall back to the next precedence layer."""
    if scope_type == models.ExternalCredentialScopeEnum.COMPANY:
        _ensure_company_scope_allowed(current_user)

    repository = BasicGenerationTemplateRepository(session)
    deleted = repository.delete_config(
        scope_type=scope_type,
        current_user=current_user,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template básico não encontrado.",
        )
    return schemas.Msg(msg="Template básico removido com sucesso.")
