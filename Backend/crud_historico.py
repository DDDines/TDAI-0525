from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import models, schemas


class _HistoricoCrudWorkflow:
    def __init__(self, runtime: Optional["_HistoricoCrudRuntime"] = None) -> None:
        self._runtime = runtime or _HistoricoCrudRuntime()

    def create_registro_historico(
        self,
        db: Session,
        registro_in: schemas.RegistroHistoricoCreate,
    ) -> models.RegistroHistorico:
        return self._runtime.create_registro_historico(db=db, registro_in=registro_in)

    def get_registros_historico(
        self,
        db: Session,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        entidade: Optional[str] = None,
        acao: Optional[models.TipoAcaoSistemaEnum] = None,
    ) -> List[models.RegistroHistorico]:
        return self._runtime.get_registros_historico(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            entidade=entidade,
            acao=acao,
        )

    def count_registros_historico(
        self,
        db: Session,
        user_id: Optional[int] = None,
        entidade: Optional[str] = None,
        acao: Optional[models.TipoAcaoSistemaEnum] = None,
    ) -> int:
        return self._runtime.count_registros_historico(
            db=db,
            user_id=user_id,
            entidade=entidade,
            acao=acao,
        )


class _HistoricoCrudRuntime:
    def create_registro_historico(
        self,
        db: Session,
        registro_in: schemas.RegistroHistoricoCreate,
    ) -> models.RegistroHistorico:
        db_obj = models.RegistroHistorico(**registro_in.model_dump(exclude_unset=True))
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_registros_historico(
        self,
        db: Session,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        entidade: Optional[str] = None,
        acao: Optional[models.TipoAcaoSistemaEnum] = None,
    ) -> List[models.RegistroHistorico]:
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
        self,
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


_historico_crud_workflow = _HistoricoCrudWorkflow()
HistoricoCrudWorkflow = _HistoricoCrudWorkflow


def get_historico_crud_workflow() -> HistoricoCrudWorkflow:
    return _historico_crud_workflow

