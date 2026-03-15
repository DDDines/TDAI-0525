"""Camada de transporte HTTP para o dominio 'historico'."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.routers import auth_utils


router = APIRouter(
    prefix="/historico",
    tags=["historico"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class HistoricoRequestService:
    """Servico request-scoped do router de historico."""

    def __init__(
        self,
        session=Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Historico Request Service."""
        self._historico_repo = HistoricoRepository(session)

    def list_historico(
        self,
        *,
        current_user: models.User,
        skip: int,
        limit: int,
        entidade: Optional[str],
        acao: Optional[str],
    ) -> schemas.HistoricoPage:
        """Execute list historico as part of this module workflow."""
        user_id_filter = None if current_user.is_superuser else current_user.id
        try:
            acao_enum = models.TipoAcaoSistemaEnum(acao) if acao else None
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="acao invalida",
            ) from exc
        items = self._historico_repo.get_registros_historico(
            user_id=user_id_filter,
            skip=skip,
            limit=limit,
            entidade=entidade,
            acao=acao_enum,
        )
        total = self._historico_repo.count_registros_historico(
            user_id=user_id_filter,
            entidade=entidade,
            acao=acao_enum,
        )
        page = skip // limit + 1
        return schemas.HistoricoPage(
            items=items,
            total_items=total,
            page=page,
            limit=limit,
        )

    @staticmethod
    def get_tipos_acao() -> List[str]:
        """Retrieve tipos acao using the current service dependencies."""
        return [enum_member.value for enum_member in models.TipoAcaoEnum]


@router.get("/", response_model=schemas.HistoricoPage)
def list_historico(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    entidade: Optional[str] = Query(None, description="Filtrar por entidade"),
    acao: Optional[str] = Query(None, description="Filtrar por tipo de acao do sistema"),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: HistoricoRequestService = Depends(),
):
    """Execute list historico as part of this module workflow."""
    return request_service.list_historico(
        current_user=current_user,
        skip=skip,
        limit=limit,
        entidade=entidade,
        acao=acao,
    )


@router.get("/tipos", response_model=List[str])
def get_tipos_acao(request_service: HistoricoRequestService = Depends()):
    """Retrieve tipos acao using the current service dependencies."""
    return request_service.get_tipos_acao()
