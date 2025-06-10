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


@router.get("/", response_model=schemas.HistoricoPage)
def list_historico(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    user_id_filter = None if current_user.is_superuser else current_user.id
    items = crud_historico.get_registros_historico(
        db, user_id=user_id_filter, skip=skip, limit=limit
    )
    total = crud_historico.count_registros_historico(db, user_id=user_id_filter)
    page = skip // limit + 1
    return {"items": items, "total_items": total, "page": page, "limit": limit}


@router.get("/tipos", response_model=List[str])
def get_tipos_acao(db: Session = Depends(database.get_db)):
    """Retorna todos os valores possíveis de TipoAcaoEnum."""
    return [enum_member.value for enum_member in models.TipoAcaoEnum]
