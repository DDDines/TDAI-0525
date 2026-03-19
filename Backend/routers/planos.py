"""Planos e faturamento — listagem de planos e alteração do plano do usuário."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.config import settings

from . import auth_utils

router = APIRouter(
    prefix="/planos",
    tags=["Planos e Faturamento"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class MudarPlanoRequest(BaseModel):
    """Payload para alterar o plano do usuário autenticado."""

    plano_id: int


@router.get("/", response_model=list[schemas.PlanoResponse])
def listar_planos(
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    current_user: models.User = Depends(  # noqa: ARG001
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Lista todos os planos disponíveis para contratação."""
    return session.query(models.Plano).order_by(models.Plano.preco_mensal).all()


@router.get("/meu-plano", response_model=schemas.PlanoResponse | None)
def meu_plano(
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Retorna o plano do usuário autenticado, ou null se não houver plano associado."""
    db_user = session.query(models.User).filter(models.User.id == current_user.id).first()
    if not db_user or not db_user.plano_id:
        return None
    return db_user.plano


@router.post("/mudar", response_model=schemas.PlanoResponse)
def mudar_plano(
    payload: MudarPlanoRequest,
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Altera o plano do usuário autenticado.

    Nota: sem integração de pagamento — apenas troca o plano no banco de dados.
    Integração com Stripe/MercadoPago pode ser adicionada aqui.
    """
    plano = session.query(models.Plano).filter(models.Plano.id == payload.plano_id).first()
    if not plano:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano não encontrado.",
        )

    db_user = session.query(models.User).filter(models.User.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    db_user.plano_id = plano.id
    session.commit()
    session.refresh(plano)
    return plano


# Trailing-slash compat
router.add_api_route(
    "/",
    listar_planos,
    methods=["GET"],
    response_model=list[schemas.PlanoResponse],
    include_in_schema=False,
)
router.add_api_route(
    "/meu-plano/",
    meu_plano,
    methods=["GET"],
    response_model=schemas.PlanoResponse | None,
    include_in_schema=False,
)
router.add_api_route(
    "/mudar/",
    mudar_plano,
    methods=["POST"],
    response_model=schemas.PlanoResponse,
    include_in_schema=False,
)
