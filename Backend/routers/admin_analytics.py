"""Camada de transporte HTTP para o dominio 'admin_analytics'."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session
from Backend import models
from Backend import schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.user_repository import UserRepository
from . import auth_utils

class _ModuleAliasProviders:

    @staticmethod
    def get_admin_analytics_router_workflow():
        return AdminAnalyticsRouterWorkflow(runtime=_AdminAnalyticsRouterRuntime())
router = APIRouter()
logger = get_logger(__name__)

class _AdminAnalyticsRouterWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'admin_analytics'."""

    def __init__(self, runtime: Optional['_AdminAnalyticsRouterRuntime']=None) -> None:
        self._runtime = runtime or _AdminAnalyticsRouterRuntime()

    async def get_current_active_admin_user(self, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)) -> models.User:
        if not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Acesso negado: requer privilegios de administrador.')
        return current_user

    def get_total_counts(self, db: Session) -> schemas.TotalCounts:
        try:
            total_usuarios = self._runtime.count_total_usuarios(db=db)
            total_produtos = self._runtime.count_total_produtos(db=db)
            total_fornecedores = self._runtime.count_total_fornecedores(db=db)
            now = self._runtime.now_utc()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            total_geracoes_ia_mes = self._runtime.count_total_geracoes_ia_mes(db=db, start_of_month=start_of_month)
            total_enriquecimentos_mes = self._runtime.count_total_enriquecimentos_mes(db=db, start_of_month=start_of_month)
            return schemas.TotalCounts(total_usuarios=total_usuarios, total_produtos=total_produtos, total_fornecedores=total_fornecedores, total_geracoes_ia_mes=total_geracoes_ia_mes, total_enriquecimentos_mes=total_enriquecimentos_mes)
        except Exception as exc:
            logger.error('Erro ao buscar contagens de admin: %s', exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao buscar estatisticas.')

    def get_uso_ia_por_plano(self, db: Session) -> List[schemas.UsoIAPorPlano]:
        planos = self._runtime.get_planos(db=db, skip=0, limit=1000)
        resultado: List[schemas.UsoIAPorPlano] = []
        now = self._runtime.now_utc()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for plano in planos:
            count = self._runtime.count_uso_ia_for_plano(db=db, plano_id=plano.id, start_of_month=start_of_month)
            resultado.append(schemas.UsoIAPorPlano(plano_id=plano.id, nome_plano=plano.nome, total_geracoes_ia_no_mes=count))
        return resultado

    def get_uso_ia_por_tipo(self, db: Session) -> List[schemas.UsoIAPorTipo]:
        now = self._runtime.now_utc()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query_result = self._runtime.get_uso_ia_por_tipo_since(db=db, start_of_month=start_of_month)
        return [schemas.UsoIAPorTipo(tipo_geracao=row.tipo_acao, total_no_mes=row.total_no_mes) for row in query_result]

    def get_user_activity(self, db: Session, *, skip: int, limit: int) -> List[schemas.UserActivity]:
        users = self._runtime.get_users(db=db, skip=skip, limit=limit)
        activities: List[schemas.UserActivity] = []
        now = self._runtime.now_utc()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for user_model in users:
            total_produtos_user = self._runtime.count_produtos_for_user(db=db, user_id=user_model.id)
            total_ia_mes_user = self._runtime.count_ia_for_user_since(db=db, user_id=user_model.id, start_of_month=start_of_month)
            activities.append(schemas.UserActivity(user_id=user_model.id, email=user_model.email, nome_completo=user_model.nome_completo, created_at=user_model.created_at, total_produtos=total_produtos_user, total_geracoes_ia_mes_corrente=total_ia_mes_user))
        return activities

    def get_product_status_counts(self, db: Session) -> List[schemas.ProductStatusCount]:
        results = self._runtime.get_product_status_counts(db=db)
        return [schemas.ProductStatusCount(status=row[0], total=row.total) for row in results]

    def get_recent_activities(self, db: Session, *, limit: int) -> List[schemas.RecentActivity]:
        registros = self._runtime.get_recent_registros_uso_ia(db=db, limit=limit)
        activities: List[schemas.RecentActivity] = []
        for reg in registros:
            user = self._runtime.get_user_by_id(db=db, user_id=reg.user_id)
            activities.append(schemas.RecentActivity(id=reg.id, user_id=reg.user_id, user_email=user.email if user else None, tipo_acao=reg.tipo_acao, created_at=reg.created_at))
        return activities

    def get_recent_historico(self, db: Session, *, limit: int) -> List[schemas.RegistroHistoricoResponse]:
        return self._runtime.get_registros_historico(db=db, skip=0, limit=limit)

class _AdminAnalyticsRouterRuntime:
    """Runtime OO com integrações e queries do router de analytics."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def count_total_usuarios(self, *, db: Session) -> int:
        return db.query(func.count(models.User.id)).scalar() or 0

    def count_total_produtos(self, *, db: Session) -> int:
        return db.query(func.count(models.Produto.id)).scalar() or 0

    def count_total_fornecedores(self, *, db: Session) -> int:
        return db.query(func.count(models.Fornecedor.id)).scalar() or 0

    def count_total_geracoes_ia_mes(self, *, db: Session, start_of_month: datetime) -> int:
        return db.query(func.count(models.RegistroUsoIA.id)).filter(models.RegistroUsoIA.created_at >= start_of_month).scalar() or 0

    def count_total_enriquecimentos_mes(self, *, db: Session, start_of_month: datetime) -> int:
        return db.query(func.count(models.RegistroUsoIA.id)).filter(models.RegistroUsoIA.created_at >= start_of_month, cast(models.RegistroUsoIA.tipo_acao, String).ilike('%enriquecimento_web%')).scalar() or 0

    def get_planos(self, *, db: Session, skip: int, limit: int):
        return UserRepository(db).get_planos(skip=skip, limit=limit)

    def count_uso_ia_for_plano(self, *, db: Session, plano_id: int, start_of_month: datetime) -> int:
        return db.query(func.count(models.RegistroUsoIA.id)).join(models.User, models.RegistroUsoIA.user_id == models.User.id).filter(models.User.plano_id == plano_id, models.RegistroUsoIA.created_at >= start_of_month).scalar() or 0

    def get_uso_ia_por_tipo_since(self, *, db: Session, start_of_month: datetime):
        return db.query(models.RegistroUsoIA.tipo_acao, func.count(models.RegistroUsoIA.id).label('total_no_mes')).filter(models.RegistroUsoIA.created_at >= start_of_month).group_by(models.RegistroUsoIA.tipo_acao).all()

    def get_users(self, *, db: Session, skip: int, limit: int):
        return UserRepository(db).get_users(skip=skip, limit=limit)

    def count_produtos_for_user(self, *, db: Session, user_id: int) -> int:
        return db.query(func.count(models.Produto.id)).filter(models.Produto.user_id == user_id).scalar() or 0

    def count_ia_for_user_since(self, *, db: Session, user_id: int, start_of_month: datetime) -> int:
        return db.query(func.count(models.RegistroUsoIA.id)).filter(models.RegistroUsoIA.user_id == user_id, models.RegistroUsoIA.created_at >= start_of_month).scalar() or 0

    def get_product_status_counts(self, *, db: Session):
        return db.query(models.Produto.status_enriquecimento_web, func.count(models.Produto.id).label('total')).group_by(models.Produto.status_enriquecimento_web).all()

    def get_recent_registros_uso_ia(self, *, db: Session, limit: int):
        return db.query(models.RegistroUsoIA).order_by(models.RegistroUsoIA.created_at.desc()).limit(limit).all()

    def get_user_by_id(self, *, db: Session, user_id: int):
        return db.get(models.User, user_id)

    def get_registros_historico(self, *, db: Session, skip: int, limit: int):
        return HistoricoRepository(db).get_registros_historico(skip=skip, limit=limit)
AdminAnalyticsRouterWorkflow = _AdminAnalyticsRouterWorkflow

class _AdminAnalyticsDependencies:

    @staticmethod
    async def get_current_active_admin_user(current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)):
        """Dependencia HTTP para garantir que o usuario autenticado e administrador."""
        workflow = _ModuleAliasProviders.get_admin_analytics_router_workflow()
        return await workflow.get_current_active_admin_user(current_user=current_user)

class _AdminAnalyticsRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'admin_analytics'."""

    def __init__(self, db: Session, workflow: AdminAnalyticsRouterWorkflow | None=None) -> None:
        self._db = db
        self._workflow = workflow or _ModuleAliasProviders.get_admin_analytics_router_workflow()

    def get_total_counts(self) -> schemas.TotalCounts:
        return self._workflow.get_total_counts(db=self._db)

    def get_uso_ia_por_plano(self) -> List[schemas.UsoIAPorPlano]:
        return self._workflow.get_uso_ia_por_plano(db=self._db)

    def get_uso_ia_por_tipo(self) -> List[schemas.UsoIAPorTipo]:
        return self._workflow.get_uso_ia_por_tipo(db=self._db)

    def get_user_activity(self, *, skip: int, limit: int) -> List[schemas.UserActivity]:
        return self._workflow.get_user_activity(db=self._db, skip=skip, limit=limit)

    def get_product_status_counts(self) -> List[schemas.ProductStatusCount]:
        return self._workflow.get_product_status_counts(db=self._db)

    def get_recent_activities(self, *, limit: int) -> List[schemas.RecentActivity]:
        return self._workflow.get_recent_activities(db=self._db, limit=limit)

    def get_recent_historico(self, *, limit: int) -> List[schemas.RegistroHistoricoResponse]:
        return self._workflow.get_recent_historico(db=self._db, limit=limit)
_build_admin_analytics_request_workflow = ServiceContainerDependencySupport.build_request_scoped_dependency(lambda session: _AdminAnalyticsRequestScope(db=session))

class _EndpointHandlers:

    @router.get('/counts', response_model=schemas.TotalCounts, dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_total_counts_endpoint(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_total_counts_endpoint)."""
        return request_workflow.get_total_counts()

    @router.get('/uso-ia/por-plano', response_model=List[schemas.UsoIAPorPlano], dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_uso_ia_por_plano_endpoint(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_uso_ia_por_plano_endpoint)."""
        return request_workflow.get_uso_ia_por_plano()

    @router.get('/uso-ia/por-tipo', response_model=List[schemas.UsoIAPorTipo], dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_uso_ia_por_tipo_endpoint(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_uso_ia_por_tipo_endpoint)."""
        return request_workflow.get_uso_ia_por_tipo()

    @router.get('/user-activity/', response_model=List[schemas.UserActivity], dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_user_activity_endpoint(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow), skip: int=Query(0, ge=0), limit: int=Query(100, ge=1, le=200)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_user_activity_endpoint)."""
        return request_workflow.get_user_activity(skip=skip, limit=limit)

    @router.get('/product-status-counts', response_model=List[schemas.ProductStatusCount], dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_product_status_counts(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_product_status_counts)."""
        return request_workflow.get_product_status_counts()

    @router.get('/recent-activities', response_model=List[schemas.RecentActivity], dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_recent_activities(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow), limit: int=Query(10, ge=1, le=50)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_recent_activities)."""
        return request_workflow.get_recent_activities(limit=limit)

    @router.get('/recent-historico', response_model=List[schemas.RegistroHistoricoResponse], dependencies=[Depends(_AdminAnalyticsDependencies.get_current_active_admin_user)])
    async def get_recent_historico(request_workflow: _AdminAnalyticsRequestScope=Depends(_build_admin_analytics_request_workflow), limit: int=Query(10, ge=1, le=50)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_recent_historico)."""
        return request_workflow.get_recent_historico(limit=limit)
