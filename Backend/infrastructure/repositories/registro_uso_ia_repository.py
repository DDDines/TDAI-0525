"""Repositorio de infraestrutura orientado a objetos para 'registro_uso_ia_repository'."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from Backend import models, schemas


class RegistroUsoIARepository:
    """Repository OO de registros de uso IA com Session vinculada por request."""

    def __init__(self, db: Session) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._db = db

    @staticmethod
    def _normalize_tipo_acao(tipo_acao: Optional[models.TipoAcaoEnum]):
        """Run normalize tipo acao in this workflow."""
        if isinstance(tipo_acao, str):
            try:
                return models.TipoAcaoEnum(tipo_acao)
            except ValueError as exc:
                raise ValueError(f"tipo_acao invalido: {tipo_acao}") from exc
        return tipo_acao

    def create_registro_uso_ia(
        self,
        registro_uso: schemas.RegistroUsoIACreate,
    ) -> models.RegistroUsoIA:
        """Create registro uso ia for this workflow."""
        db_obj = models.RegistroUsoIA(**registro_uso.model_dump(exclude_unset=True))
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return db_obj

    def get_registro_uso_ia(self, *, registro_id: int) -> Optional[models.RegistroUsoIA]:
        """Return one IA usage record by identifier."""
        return (
            self._db.query(models.RegistroUsoIA)
            .filter(models.RegistroUsoIA.id == registro_id)
            .first()
        )

    def get_registros_uso_ia(
        self,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tipo_acao: Optional[models.TipoAcaoEnum] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> List[models.RegistroUsoIA]:
        """Return registros uso ia for this workflow."""
        normalized_tipo_acao = self._normalize_tipo_acao(tipo_acao)
        query = self._db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.user_id == user_id)
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
        *,
        user_id: int,
        tipo_acao: Optional[models.TipoAcaoEnum] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> int:
        """Count registros uso ia for this workflow."""
        normalized_tipo_acao = self._normalize_tipo_acao(tipo_acao)
        query = self._db.query(func.count(models.RegistroUsoIA.id)).filter(
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
        *,
        produto_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[models.RegistroUsoIA]:
        """Return usos ia by produto for this workflow."""
        return (
            self._db.query(models.RegistroUsoIA)
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
        *,
        user_id: int,
        tipo_geracao_prefix: str,
    ) -> int:
        """Count usos ia by user and type no mes corrente for this workflow."""
        inicio_mes = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        tipo_col = cast(models.RegistroUsoIA.tipo_acao, String)
        if self._db.bind and self._db.bind.dialect.name == "postgresql":
            tipo_filter = tipo_col.ilike(f"{tipo_geracao_prefix}%")
        else:
            tipo_filter = func.lower(tipo_col).like(f"{tipo_geracao_prefix.lower()}%")

        return (
            self._db.query(func.count(models.RegistroUsoIA.id))
            .filter(
                models.RegistroUsoIA.user_id == user_id,
                models.RegistroUsoIA.created_at >= inicio_mes,
                tipo_filter,
            )
            .scalar()
            or 0
        )

    def get_geracoes_ia_count_no_mes_corrente(self, *, user_id: int) -> int:
        """Return geracoes ia count no mes corrente for this workflow."""
        inicio_mes = (
            datetime.now(timezone.utc)
            .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            .replace(tzinfo=None)
        )
        return (
            self._db.query(func.count(models.RegistroUsoIA.id))
            .filter(
                models.RegistroUsoIA.user_id == user_id,
                models.RegistroUsoIA.created_at >= inicio_mes,
            )
            .scalar()
            or 0
        )
