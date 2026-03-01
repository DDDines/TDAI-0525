"""Camada de transporte HTTP para o dominio 'historico'."""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from . import auth_utils
router = APIRouter(prefix='/historico', tags=['historico'], dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)])

class _HistoricoRuntime:
    """Runtime OO para operacoes de historico com session request-scoped."""

    def __init__(self, historico_repo: HistoricoRepository) -> None:
        self._historico_repo = historico_repo

    def get_registros_historico(self, *, user_id: int | None, skip: int, limit: int):
        return self._historico_repo.get_registros_historico(user_id=user_id, skip=skip, limit=limit)

    def count_registros_historico(self, *, user_id: int | None) -> int:
        return self._historico_repo.count_registros_historico(user_id=user_id)

    @staticmethod
    def get_tipos_acao() -> List[str]:
        return [enum_member.value for enum_member in models.TipoAcaoEnum]

class _HistoricoWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'historico'."""

    def __init__(self, runtime: _HistoricoRuntime) -> None:
        self._runtime = runtime

    def list_historico(self, *, db=None, current_user: models.User, skip: int, limit: int) -> schemas.HistoricoPage:
        user_id_filter = None if current_user.is_superuser else current_user.id
        try:
            items = self._runtime.get_registros_historico(user_id=user_id_filter, skip=skip, limit=limit)
        except TypeError:
            items = self._runtime.get_registros_historico(db, user_id=user_id_filter, skip=skip, limit=limit)
        try:
            total = self._runtime.count_registros_historico(user_id=user_id_filter)
        except TypeError:
            total = self._runtime.count_registros_historico(db, user_id=user_id_filter)
        page = skip // limit + 1
        return schemas.HistoricoPage(items=items, total_items=total, page=page, limit=limit)

    def get_tipos_acao(self) -> List[str]:
        return self._runtime.get_tipos_acao()
HistoricoWorkflow = _HistoricoWorkflow
_build_historico_workflow = ServiceContainerDependencySupport.build_request_scoped_dependency(lambda session: _HistoricoWorkflow(runtime=_HistoricoRuntime(historico_repo=HistoricoRepository(session))))

class _EndpointHandlers:

    @router.get('/', response_model=schemas.HistoricoPage)
    def list_historico(skip: int=Query(0, ge=0), limit: int=Query(10, ge=1, le=100), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), workflow: _HistoricoWorkflow=Depends(_build_historico_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (list_historico)."""
        return workflow.list_historico(current_user=current_user, skip=skip, limit=limit)

    @router.get('/tipos', response_model=List[str])
    def get_tipos_acao(workflow: _HistoricoWorkflow=Depends(_build_historico_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_tipos_acao)."""
        return workflow.get_tipos_acao()
