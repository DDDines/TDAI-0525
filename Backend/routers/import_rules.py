"""Router HTTP para regras de validacao aprendidas."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.import_validation_memory_service import (
    ImportValidationMemoryService,
)
from Backend.application.services.service_container import ServiceContainerDependencySupport

from . import auth_utils

router = APIRouter(
    prefix="/import-rules",
    tags=["Regras de Validacao"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
    redirect_slashes=False,
)


@router.get("", response_model=List[schemas.ImportValidationRuleResponse])
def listar_regras(
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Lista todas as regras de validacao aprendidas do usuario."""
    svc = ImportValidationMemoryService(db=session, models=models, schemas=schemas)
    return svc.list_rules(user_id=current_user.id)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_regra(
    rule_id: int,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Remove uma regra de validacao aprendida."""
    svc = ImportValidationMemoryService(db=session, models=models, schemas=schemas)
    deleted = svc.delete_rule(rule_id=rule_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra nao encontrada")
    session.commit()
