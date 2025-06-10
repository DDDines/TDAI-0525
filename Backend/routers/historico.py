from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from Backend.database import get_db
from Backend import models
from . import auth_utils

router = APIRouter(
    prefix="/historico",
    tags=["Histórico de IA"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

@router.get("/tipos", response_model=List[str])
def get_tipos_acao(db: Session = Depends(get_db)):
    """Retorna todos os valores possíveis de TipoAcaoIAEnum."""
    return [enum_member.value for enum_member in models.TipoAcaoIAEnum]
