from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import models, schemas


def create_registro_historico(db: Session, registro_in: schemas.RegistroHistoricoCreate) -> models.RegistroHistorico:
    db_obj = models.RegistroHistorico(**registro_in.model_dump(exclude_unset=True))
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_registros_historico(
    db: Session,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    entidade: Optional[str] = None,
    acao: Optional[models.TipoAcaoSistemaEnum] = None,
) -> List[models.RegistroHistorico]:
    if skip < 0:
        raise ValueError("skip must be non-negative")
    if limit <= 0:
        raise ValueError("limit must be positive")
    query = db.query(models.RegistroHistorico)
    if user_id is not None:
        query = query.filter(models.RegistroHistorico.user_id == user_id)
    if entidade:
        query = query.filter(models.RegistroHistorico.entidade == entidade)
    if acao:
        query = query.filter(models.RegistroHistorico.acao == acao)
    return (
        query.order_by(models.RegistroHistorico.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_registros_historico(
    db: Session,
    user_id: Optional[int] = None,
    entidade: Optional[str] = None,
    acao: Optional[models.TipoAcaoSistemaEnum] = None,
) -> int:
    query = db.query(func.count(models.RegistroHistorico.id))
    if user_id is not None:
        query = query.filter(models.RegistroHistorico.user_id == user_id)
    if entidade:
        query = query.filter(models.RegistroHistorico.entidade == entidade)
    if acao:
        query = query.filter(models.RegistroHistorico.acao == acao)
    return query.scalar() or 0
