from Backend.core.deprecation import deprecated_legacy_service_proxy
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from Backend import crud_historico
from Backend import database, models, schemas
from . import auth_utils

router = APIRouter(
    prefix="/historico",
    tags=["historico"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)


class _HistoricoRuntime:
    """Runtime OO para operaÃ§Ãµes de histÃ³rico."""

    def get_registros_historico(
        self,
        db: Session,
        *,
        user_id: int | None,
        skip: int,
        limit: int,
    ):
        return crud_historico.get_registros_historico(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    def count_registros_historico(self, db: Session, *, user_id: int | None) -> int:
        return crud_historico.count_registros_historico(db, user_id=user_id)

    def get_tipos_acao(self) -> List[str]:
        return [enum_member.value for enum_member in models.TipoAcaoEnum]


class _HistoricoWorkflow:
    def __init__(self, runtime: _HistoricoRuntime | None = None) -> None:
        self._runtime = runtime or _HistoricoRuntime()

    def list_historico(
        self,
        db: Session,
        current_user: models.User,
        skip: int,
        limit: int,
    ) -> schemas.HistoricoPage:
        user_id_filter = None if current_user.is_superuser else current_user.id
        items = self._runtime.get_registros_historico(
            db,
            user_id=user_id_filter,
            skip=skip,
            limit=limit,
        )
        total = self._runtime.count_registros_historico(db, user_id=user_id_filter)
        page = skip // limit + 1
        return schemas.HistoricoPage(
            items=items,
            total_items=total,
            page=page,
            limit=limit,
        )

    def get_tipos_acao(self) -> List[str]:
        return self._runtime.get_tipos_acao()


_historico_runtime = _HistoricoRuntime()
_historico_workflow = _HistoricoWorkflow(runtime=_historico_runtime)


@router.get("/", response_model=schemas.HistoricoPage)
def list_historico(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return _historico_workflow.list_historico(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get("/tipos", response_model=List[str])
def get_tipos_acao(db: Session = Depends(database.get_db)):
    _ = db
    return _historico_workflow.get_tipos_acao()


class HistoricoRouterLegacyService:
    """Camada de compatibilidade para chamadas legadas do router."""

    def list_historico(self, *args, **kwargs):
        return _historico_workflow.list_historico(*args, **kwargs)

    def get_tipos_acao(self, *args, **kwargs):
        return _historico_workflow.get_tipos_acao(*args, **kwargs)


historico_router_legacy_service = deprecated_legacy_service_proxy(
    HistoricoRouterLegacyService(),
    qualified_name="Backend.routers.historico.historico_router_legacy_service",
)
