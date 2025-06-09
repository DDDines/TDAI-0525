from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import models, schemas


def create_registro_uso_ia(db: Session, registro_uso: schemas.RegistroUsoIACreate) -> models.RegistroUsoIA:
    db_obj = models.RegistroUsoIA(**registro_uso.model_dump(exclude_unset=True))
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_registros_uso_ia(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    tipo_acao: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
) -> List[models.RegistroUsoIA]:
    query = db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.user_id == user_id)
    if tipo_acao:
        query = query.filter(models.RegistroUsoIA.tipo_acao == tipo_acao)
    if data_inicio:
        query = query.filter(models.RegistroUsoIA.created_at >= data_inicio)
    if data_fim:
        query = query.filter(models.RegistroUsoIA.created_at <= data_fim)
    return (
        query.order_by(models.RegistroUsoIA.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_registros_uso_ia(
    db: Session,
    user_id: int,
    tipo_acao: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
) -> int:
    query = db.query(func.count(models.RegistroUsoIA.id)).filter(models.RegistroUsoIA.user_id == user_id)
    if tipo_acao:
        query = query.filter(models.RegistroUsoIA.tipo_acao == tipo_acao)
    if data_inicio:
        query = query.filter(models.RegistroUsoIA.created_at >= data_inicio)
    if data_fim:
        query = query.filter(models.RegistroUsoIA.created_at <= data_fim)
    return query.scalar() or 0


def get_usos_ia_by_produto(
    db: Session,
    produto_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> List[models.RegistroUsoIA]:
    return (
        db.query(models.RegistroUsoIA)
        .filter(
            models.RegistroUsoIA.produto_id == produto_id,
            models.RegistroUsoIA.user_id == user_id,
        )
        .order_by(models.RegistroUsoIA.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_usos_ia_by_user_and_type_no_mes_corrente(
    db: Session,
    user_id: int,
    tipo_geracao_prefix: str,
) -> int:
    inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(models.RegistroUsoIA.id))
        .filter(
            models.RegistroUsoIA.user_id == user_id,
            models.RegistroUsoIA.created_at >= inicio_mes,
            models.RegistroUsoIA.tipo_acao.ilike(f"{tipo_geracao_prefix}%"),
        )
        .scalar()
        or 0
    )


def get_geracoes_ia_count_no_mes_corrente(db: Session, user_id: int) -> int:
    inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(models.RegistroUsoIA.id))
        .filter(
            models.RegistroUsoIA.user_id == user_id,
            models.RegistroUsoIA.created_at >= inicio_mes,
        )
        .scalar()
        or 0
    )
