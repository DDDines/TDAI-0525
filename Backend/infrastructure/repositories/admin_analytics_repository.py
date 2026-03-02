"""Repository queries used by administrative analytics endpoints."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from Backend import models


class AdminAnalyticsRepository:
    """Encapsulate analytics-focused aggregate queries in one repository."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with request-scoped SQLAlchemy session."""
        self._db = db

    def count_total_users(self) -> int:
        """Return total user count."""
        return self._db.query(func.count(models.User.id)).scalar() or 0

    def count_total_products(self) -> int:
        """Return total product count."""
        return self._db.query(func.count(models.Produto.id)).scalar() or 0

    def count_total_suppliers(self) -> int:
        """Return total supplier count."""
        return self._db.query(func.count(models.Fornecedor.id)).scalar() or 0

    def count_ia_usage_since(self, *, start_at: datetime) -> int:
        """Return IA usage count from a given datetime boundary."""
        return (
            self._db.query(func.count(models.RegistroUsoIA.id))
            .filter(models.RegistroUsoIA.created_at >= start_at)
            .scalar()
            or 0
        )

    def count_web_enrichment_usage_since(self, *, start_at: datetime) -> int:
        """Return web-enrichment usage count from a given datetime boundary."""
        return (
            self._db.query(func.count(models.RegistroUsoIA.id))
            .filter(
                models.RegistroUsoIA.created_at >= start_at,
                cast(models.RegistroUsoIA.tipo_acao, String).ilike("%enriquecimento_web%"),
            )
            .scalar()
            or 0
        )

    def count_plan_usage_since(self, *, plano_id: int, start_at: datetime) -> int:
        """Return IA usage count for one plan from a datetime boundary."""
        return (
            self._db.query(func.count(models.RegistroUsoIA.id))
            .join(models.User, models.RegistroUsoIA.user_id == models.User.id)
            .filter(
                models.User.plano_id == plano_id,
                models.RegistroUsoIA.created_at >= start_at,
            )
            .scalar()
            or 0
        )

    def list_usage_by_action_since(self, *, start_at: datetime):
        """Return grouped IA usage counts by action type from a datetime boundary."""
        return (
            self._db.query(
                models.RegistroUsoIA.tipo_acao,
                func.count(models.RegistroUsoIA.id).label("total_no_mes"),
            )
            .filter(models.RegistroUsoIA.created_at >= start_at)
            .group_by(models.RegistroUsoIA.tipo_acao)
            .all()
        )

    def count_products_by_user(self, *, user_id: int) -> int:
        """Return total product count for one user."""
        return (
            self._db.query(func.count(models.Produto.id))
            .filter(models.Produto.user_id == user_id)
            .scalar()
            or 0
        )

    def count_ia_usage_by_user_since(self, *, user_id: int, start_at: datetime) -> int:
        """Return IA usage count for one user from a datetime boundary."""
        return (
            self._db.query(func.count(models.RegistroUsoIA.id))
            .filter(
                models.RegistroUsoIA.user_id == user_id,
                models.RegistroUsoIA.created_at >= start_at,
            )
            .scalar()
            or 0
        )

    def list_product_status_counts(self):
        """Return grouped product counts by enrichment status."""
        return (
            self._db.query(
                models.Produto.status_enriquecimento_web,
                func.count(models.Produto.id).label("total"),
            )
            .group_by(models.Produto.status_enriquecimento_web)
            .all()
        )

    def list_recent_usage_records(self, *, limit: int):
        """Return most recent IA usage records limited by quantity."""
        return (
            self._db.query(models.RegistroUsoIA)
            .order_by(models.RegistroUsoIA.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_user_by_id(self, *, user_id: int):
        """Return one user by identifier."""
        return self._db.get(models.User, user_id)
