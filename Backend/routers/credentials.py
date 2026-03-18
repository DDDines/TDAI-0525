"""Endpoints for client-managed external API credentials."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.config import settings
from Backend.infrastructure.repositories.external_credential_repository import (
    ExternalCredentialRepository,
)

from . import auth_utils

router = APIRouter(
    prefix="/credenciais",
    tags=["credenciais"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class _CredentialEndpointHelpers:
    """Static helpers shared across credential endpoints."""

    @staticmethod
    def _ensure_company_scope_allowed(current_user: models.User) -> None:
        """Restrict company-scoped credential changes to admins/owners."""
        role_name = str(getattr(getattr(current_user, "role", None), "name", "") or "").strip().lower()
        if current_user.is_superuser or role_name == "admin":
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente administradores podem gerenciar credenciais da empresa.",
        )


_ensure_company_scope_allowed = _CredentialEndpointHelpers._ensure_company_scope_allowed


@router.get("/overview", response_model=schemas.CredentialsOverviewResponse)
def read_credentials_overview(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Return company credentials, personal overrides and effective sources."""
    repository = ExternalCredentialRepository(session)
    return repository.build_overview(current_user=current_user, settings=settings)


@router.put("", response_model=schemas.ExternalCredentialConfigResponse)
def upsert_external_credential(
    payload: schemas.ExternalCredentialConfigUpsert,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Create or update one external credential config."""
    if payload.scope_type == models.ExternalCredentialScopeEnum.COMPANY:
        _ensure_company_scope_allowed(current_user)

    repository = ExternalCredentialRepository(session)
    validation = repository.validate_payload(
        provider=payload.provider,
        secret_value=payload.secret_value,
        config_json=payload.config_json,
    )
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation["errors"],
        )
    config = repository.upsert_config(
        scope_type=payload.scope_type,
        provider=payload.provider,
        current_user=current_user,
        secret_value=payload.secret_value,
        config_json=payload.config_json,
        description=payload.description,
        is_active=payload.is_active,
    )
    return repository.serialize_config(config)


@router.delete("/{scope_type}/{provider}", response_model=schemas.Msg)
def delete_external_credential(
    scope_type: models.ExternalCredentialScopeEnum,
    provider: models.ExternalCredentialProviderEnum,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Delete one stored credential config."""
    if scope_type == models.ExternalCredentialScopeEnum.COMPANY:
        _ensure_company_scope_allowed(current_user)
    repository = ExternalCredentialRepository(session)
    deleted = repository.delete_config(
        scope_type=scope_type,
        provider=provider,
        current_user=current_user,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial nao encontrada.")
    return schemas.Msg(msg="Credencial removida com sucesso.")


@router.post("/validar")
def validate_external_credential(
    payload: schemas.ExternalCredentialConfigUpsert,
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Perform local validation for one credential payload without persisting it."""
    if payload.scope_type == models.ExternalCredentialScopeEnum.COMPANY:
        _ensure_company_scope_allowed(current_user)
    repository = ExternalCredentialRepository(session)
    existing = repository.get_config(
        scope_type=payload.scope_type,
        provider=payload.provider,
        current_user=current_user,
    )
    effective_secret = (
        payload.secret_value
        if payload.secret_value is not None and str(payload.secret_value or "").strip()
        else getattr(existing, "secret_value", None)
    )
    effective_config = dict(getattr(existing, "config_json", None) or {})
    for key, value in (payload.config_json or {}).items():
        if str(value or "").strip():
            effective_config[key] = value
    return repository.validate_payload(
        provider=payload.provider,
        secret_value=effective_secret,
        config_json=effective_config,
    )
