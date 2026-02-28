from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from Backend import models, schemas


def _normalize_tipo_acao(tipo_acao: Optional[models.TipoAcaoEnum]):
    if isinstance(tipo_acao, str):
        try:
            return models.TipoAcaoEnum(tipo_acao)
        except ValueError as exc:
            raise ValueError(f"tipo_acao invalido: {tipo_acao}") from exc
    return tipo_acao


class _RegistroUsoIACrudWorkflow:
    def __init__(self, runtime: Optional["_RegistroUsoIACrudRuntime"] = None) -> None:
        self._runtime = runtime or _RegistroUsoIACrudRuntime()

    def create_registro_uso_ia(
        self,
        db: Session,
        registro_uso: schemas.RegistroUsoIACreate,
    ) -> models.RegistroUsoIA:
        return self._runtime.create_registro_uso_ia(db=db, registro_uso=registro_uso)

    def get_registros_uso_ia(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tipo_acao: Optional[models.TipoAcaoEnum] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> List[models.RegistroUsoIA]:
        return self._runtime.get_registros_uso_ia(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
            tipo_acao=tipo_acao,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    def count_registros_uso_ia(
        self,
        db: Session,
        user_id: int,
        tipo_acao: Optional[models.TipoAcaoEnum] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> int:
        return self._runtime.count_registros_uso_ia(
            db=db,
            user_id=user_id,
            tipo_acao=tipo_acao,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    def get_usos_ia_by_produto(
        self,
        db: Session,
        produto_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[models.RegistroUsoIA]:
        return self._runtime.get_usos_ia_by_produto(
            db=db,
            produto_id=produto_id,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    def count_usos_ia_by_user_and_type_no_mes_corrente(
        self,
        db: Session,
        user_id: int,
        tipo_geracao_prefix: str,
    ) -> int:
        return self._runtime.count_usos_ia_by_user_and_type_no_mes_corrente(
            db=db,
            user_id=user_id,
            tipo_geracao_prefix=tipo_geracao_prefix,
        )

    def get_geracoes_ia_count_no_mes_corrente(self, db: Session, user_id: int) -> int:
        return self._runtime.get_geracoes_ia_count_no_mes_corrente(db=db, user_id=user_id)


class _RegistroUsoIACrudRuntime:
    def create_registro_uso_ia(
        self,
        db: Session,
        registro_uso: schemas.RegistroUsoIACreate,
    ) -> models.RegistroUsoIA:
        db_obj = models.RegistroUsoIA(**registro_uso.model_dump(exclude_unset=True))
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_registros_uso_ia(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tipo_acao: Optional[models.TipoAcaoEnum] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> List[models.RegistroUsoIA]:
        normalized_tipo_acao = _normalize_tipo_acao(tipo_acao)
        query = db.query(models.RegistroUsoIA).filter(
            models.RegistroUsoIA.user_id == user_id
        )
        if normalized_tipo_acao:
            query = query.filter(models.RegistroUsoIA.tipo_acao == normalized_tipo_acao)
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
        self,
        db: Session,
        user_id: int,
        tipo_acao: Optional[models.TipoAcaoEnum] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> int:
        normalized_tipo_acao = _normalize_tipo_acao(tipo_acao)
        query = db.query(func.count(models.RegistroUsoIA.id)).filter(
            models.RegistroUsoIA.user_id == user_id
        )
        if normalized_tipo_acao:
            query = query.filter(models.RegistroUsoIA.tipo_acao == normalized_tipo_acao)
        if data_inicio:
            query = query.filter(models.RegistroUsoIA.created_at >= data_inicio)
        if data_fim:
            query = query.filter(models.RegistroUsoIA.created_at <= data_fim)
        return query.scalar() or 0

    def get_usos_ia_by_produto(
        self,
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
        self,
        db: Session,
        user_id: int,
        tipo_geracao_prefix: str,
    ) -> int:
        inicio_mes = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        tipo_col = cast(models.RegistroUsoIA.tipo_acao, String)
        if db.bind and db.bind.dialect.name == "postgresql":
            tipo_filter = tipo_col.ilike(f"{tipo_geracao_prefix}%")
        else:
            tipo_filter = func.lower(tipo_col).like(f"{tipo_geracao_prefix.lower()}%")

        return (
            db.query(func.count(models.RegistroUsoIA.id))
            .filter(
                models.RegistroUsoIA.user_id == user_id,
                models.RegistroUsoIA.created_at >= inicio_mes,
                tipo_filter,
            )
            .scalar()
            or 0
        )

    def get_geracoes_ia_count_no_mes_corrente(self, db: Session, user_id: int) -> int:
        inicio_mes = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        return (
            db.query(func.count(models.RegistroUsoIA.id))
            .filter(
                models.RegistroUsoIA.user_id == user_id,
                models.RegistroUsoIA.created_at >= inicio_mes,
            )
            .scalar()
            or 0
        )


_registro_uso_ia_workflow = _RegistroUsoIACrudWorkflow()


def create_registro_uso_ia(
    db: Session,
    registro_uso: schemas.RegistroUsoIACreate,
) -> models.RegistroUsoIA:
    return _registro_uso_ia_workflow.create_registro_uso_ia(
        db=db,
        registro_uso=registro_uso,
    )


def get_registros_uso_ia(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    tipo_acao: Optional[models.TipoAcaoEnum] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
) -> List[models.RegistroUsoIA]:
    return _registro_uso_ia_workflow.get_registros_uso_ia(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        tipo_acao=tipo_acao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


def count_registros_uso_ia(
    db: Session,
    user_id: int,
    tipo_acao: Optional[models.TipoAcaoEnum] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
) -> int:
    return _registro_uso_ia_workflow.count_registros_uso_ia(
        db=db,
        user_id=user_id,
        tipo_acao=tipo_acao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


def get_usos_ia_by_produto(
    db: Session,
    produto_id: int,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> List[models.RegistroUsoIA]:
    return _registro_uso_ia_workflow.get_usos_ia_by_produto(
        db=db,
        produto_id=produto_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


def count_usos_ia_by_user_and_type_no_mes_corrente(
    db: Session,
    user_id: int,
    tipo_geracao_prefix: str,
) -> int:
    return _registro_uso_ia_workflow.count_usos_ia_by_user_and_type_no_mes_corrente(
        db=db,
        user_id=user_id,
        tipo_geracao_prefix=tipo_geracao_prefix,
    )


def get_geracoes_ia_count_no_mes_corrente(db: Session, user_id: int) -> int:
    return _registro_uso_ia_workflow.get_geracoes_ia_count_no_mes_corrente(
        db=db,
        user_id=user_id,
    )




