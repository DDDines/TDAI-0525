"""Historico repository.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import models, schemas


class HistoricoRepository:
    """Repository OO de Historico com Session vinculada por request."""

    def __init__(self, db: Session) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._db = db

    def create_registro_historico(
        self,
        registro_in: schemas.RegistroHistoricoCreate,
    ) -> models.RegistroHistorico:
        """Create registro historico."""
        db_obj = models.RegistroHistorico(**registro_in.model_dump(exclude_unset=True))
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return db_obj

    def get_registros_historico(
        self,
        *,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        entidade: Optional[str] = None,
        acao: Optional[models.TipoAcaoSistemaEnum] = None,
    ) -> List[models.RegistroHistorico]:
        """Return Registros historico."""
        query = self._db.query(models.RegistroHistorico)
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
        *,
        user_id: Optional[int] = None,
        entidade: Optional[str] = None,
        acao: Optional[models.TipoAcaoSistemaEnum] = None,
    ) -> int:
        """Count registros historico."""
        query = self._db.query(func.count(models.RegistroHistorico.id))
        if user_id is not None:
            query = query.filter(models.RegistroHistorico.user_id == user_id)
        if entidade:
            query = query.filter(models.RegistroHistorico.entidade == entidade)
        if acao:
            query = query.filter(models.RegistroHistorico.acao == acao)
        return query.scalar() or 0
