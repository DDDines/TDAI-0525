"""Camada de transporte HTTP para o dominio 'admin_analytics'."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.admin_analytics_repository import (
    AdminAnalyticsRepository,
)
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.user_repository import UserRepository

from . import auth_utils


router = APIRouter()
logger = get_logger(__name__)


class AdminAnalyticsRequestService:
    """Servico request-scoped para analytics administrativos."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Admin Analytics Request Service."""
        self._user_repository = UserRepository(session)
        self._historico_repository = HistoricoRepository(session)
        self._analytics_repository = AdminAnalyticsRepository(session)

    @staticmethod
    def _now_utc() -> datetime:
        """Execute now utc as part of this module workflow."""
        return datetime.now(timezone.utc)

    def get_total_counts(self) -> schemas.TotalCounts:
        """Retrieve total counts using the current service dependencies."""
        try:
            start_of_month = self._now_utc().replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            return schemas.TotalCounts(
                total_usuarios=self._analytics_repository.count_total_users(),
                total_produtos=self._analytics_repository.count_total_products(),
                total_fornecedores=self._analytics_repository.count_total_suppliers(),
                total_geracoes_ia_mes=self._analytics_repository.count_ia_usage_since(
                    start_at=start_of_month
                ),
                total_enriquecimentos_mes=self._analytics_repository.count_web_enrichment_usage_since(
                    start_at=start_of_month
                ),
            )
        except Exception as exc:
            logger.error("Erro ao buscar contagens de admin: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao buscar estatisticas.",
            ) from exc

    def get_uso_ia_por_plano(self) -> List[schemas.UsoIAPorPlano]:
        """Retrieve uso ia por plano using the current service dependencies."""
        planos = self._user_repository.get_planos(skip=0, limit=1000)
        resultado: List[schemas.UsoIAPorPlano] = []
        start_of_month = self._now_utc().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        for plano in planos:
            count = self._analytics_repository.count_plan_usage_since(
                plano_id=plano.id,
                start_at=start_of_month,
            )
            resultado.append(
                schemas.UsoIAPorPlano(
                    plano_id=plano.id,
                    nome_plano=plano.nome,
                    total_geracoes_ia_no_mes=count,
                )
            )
        return resultado

    def get_uso_ia_por_tipo(self) -> List[schemas.UsoIAPorTipo]:
        """Retrieve uso ia por tipo using the current service dependencies."""
        start_of_month = self._now_utc().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        query_result = self._analytics_repository.list_usage_by_action_since(
            start_at=start_of_month
        )
        return [
            schemas.UsoIAPorTipo(
                tipo_acao=row.tipo_acao,
                total_no_mes=row.total_no_mes,
            )
            for row in query_result
        ]

    def get_user_activity(self, *, skip: int, limit: int) -> List[schemas.UserActivity]:
        """Retrieve user activity using the current service dependencies."""
        users = self._user_repository.get_users(skip=skip, limit=limit)
        activities: List[schemas.UserActivity] = []
        start_of_month = self._now_utc().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        for user_model in users:
            total_produtos_user = self._analytics_repository.count_products_by_user(
                user_id=user_model.id
            )
            total_ia_mes_user = self._analytics_repository.count_ia_usage_by_user_since(
                user_id=user_model.id,
                start_at=start_of_month,
            )
            activities.append(
                schemas.UserActivity(
                    user_id=user_model.id,
                    email=user_model.email,
                    nome_completo=user_model.nome_completo,
                    created_at=user_model.created_at,
                    total_produtos=total_produtos_user,
                    total_geracoes_ia_mes_corrente=total_ia_mes_user,
                )
            )
        return activities

    def get_product_status_counts(self) -> List[schemas.ProductStatusCount]:
        """Retrieve product status counts using the current service dependencies."""
        results = self._analytics_repository.list_product_status_counts()
        return [schemas.ProductStatusCount(status=row[0], total=row.total) for row in results]

    def get_recent_activities(self, *, limit: int) -> List[schemas.RecentActivity]:
        """Retrieve recent activities using the current service dependencies."""
        registros = self._analytics_repository.list_recent_usage_records(limit=limit)
        activities: List[schemas.RecentActivity] = []
        for reg in registros:
            user = self._analytics_repository.get_user_by_id(user_id=reg.user_id)
            activities.append(
                schemas.RecentActivity(
                    id=reg.id,
                    user_id=reg.user_id,
                    user_email=user.email if user else None,
                    tipo_acao=reg.tipo_acao,
                    created_at=reg.created_at,
                )
            )
        return activities

    def get_recent_historico(self, *, limit: int) -> List[schemas.RegistroHistoricoResponse]:
        """Retrieve recent historico using the current service dependencies."""
        return self._historico_repository.get_registros_historico(skip=0, limit=limit)


class _AdminAnalyticsDependencies:

    """Represent Admin Analytics Dependencies and centralize its responsibilities inside this module."""
    @staticmethod
    async def get_current_active_admin_user(
        current_user: models.User = Depends(
            auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
        ),
    ):
        """Retrieve current active admin user using the current service dependencies."""
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: requer privilegios de administrador.",
            )
        return current_user


@router.get(
    "/counts",
    response_model=schemas.TotalCounts,
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_total_counts_endpoint(request_service: AdminAnalyticsRequestService = Depends()):
    """Retrieve total counts endpoint using the current service dependencies."""
    return request_service.get_total_counts()


@router.get(
    "/uso-ia/por-plano",
    response_model=List[schemas.UsoIAPorPlano],
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_uso_ia_por_plano_endpoint(request_service: AdminAnalyticsRequestService = Depends()):
    """Retrieve uso ia por plano endpoint using the current service dependencies."""
    return request_service.get_uso_ia_por_plano()


@router.get(
    "/uso-ia/por-tipo",
    response_model=List[schemas.UsoIAPorTipo],
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_uso_ia_por_tipo_endpoint(request_service: AdminAnalyticsRequestService = Depends()):
    """Retrieve uso ia por tipo endpoint using the current service dependencies."""
    return request_service.get_uso_ia_por_tipo()


@router.get(
    "/user-activity/",
    response_model=List[schemas.UserActivity],
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_user_activity_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    request_service: AdminAnalyticsRequestService = Depends(),
):
    """Retrieve user activity endpoint using the current service dependencies."""
    return request_service.get_user_activity(skip=skip, limit=limit)


@router.get(
    "/product-status-counts",
    response_model=List[schemas.ProductStatusCount],
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_product_status_counts(request_service: AdminAnalyticsRequestService = Depends()):
    """Retrieve product status counts using the current service dependencies."""
    return request_service.get_product_status_counts()


@router.get(
    "/recent-activities",
    response_model=List[schemas.RecentActivity],
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=50),
    request_service: AdminAnalyticsRequestService = Depends(),
):
    """Retrieve recent activities using the current service dependencies."""
    return request_service.get_recent_activities(limit=limit)


@router.get(
    "/recent-historico",
    response_model=List[schemas.RegistroHistoricoResponse],
    dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)],
)
async def get_recent_historico(
    limit: int = Query(10, ge=1, le=50),
    request_service: AdminAnalyticsRequestService = Depends(),
):
    """Retrieve recent historico using the current service dependencies."""
    return request_service.get_recent_historico(limit=limit)
