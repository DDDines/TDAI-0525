"""Helpers de compatibilidade runtime para repositorios legados."""

from __future__ import annotations

import logging

from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def ensure_attribute_templates_collect_in_ai(*, session: Session) -> None:
    """Garante a coluna collect_in_ai para bancos locais ainda nao migrados."""
    if not hasattr(session, "get_bind"):
        return
    bind = session.get_bind()
    if bind is None:
        return

    try:
        inspector = inspect(bind)
    except NoInspectionAvailable:
        return

    try:
        if "attribute_templates" not in inspector.get_table_names():
            return

        attribute_columns = {
            column["name"] for column in inspector.get_columns("attribute_templates")
        }
        if "collect_in_ai" in attribute_columns:
            return

        session.execute(
            text(
                "ALTER TABLE attribute_templates "
                "ADD COLUMN collect_in_ai BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        session.commit()
        session.expire_all()
        logger.warning(
            "Compatibilidade runtime aplicada: coluna collect_in_ai adicionada em attribute_templates."
        )
    except Exception as exc:  # pragma: no cover - cobertura real depende do banco local
        rollback = getattr(session, "rollback", None)
        if callable(rollback):
            rollback()
        logger.warning(
            "Falha ao garantir compatibilidade da coluna collect_in_ai: %s",
            exc,
        )


def ensure_fornecedores_logo_url(*, session: Session) -> None:
    """Garante a coluna logo_url para bancos locais ainda nao migrados."""
    if not hasattr(session, "get_bind"):
        return
    bind = session.get_bind()
    if bind is None:
        return

    try:
        inspector = inspect(bind)
    except NoInspectionAvailable:
        return

    try:
        if "fornecedores" not in inspector.get_table_names():
            return

        fornecedor_columns = {
            column["name"] for column in inspector.get_columns("fornecedores")
        }
        if "logo_url" in fornecedor_columns:
            return

        session.execute(text("ALTER TABLE fornecedores ADD COLUMN logo_url VARCHAR"))
        session.commit()
        session.expire_all()
        logger.warning(
            "Compatibilidade runtime aplicada: coluna logo_url adicionada em fornecedores."
        )
    except Exception as exc:  # pragma: no cover - cobertura real depende do banco local
        rollback = getattr(session, "rollback", None)
        if callable(rollback):
            rollback()
        logger.warning(
            "Falha ao garantir compatibilidade da coluna logo_url: %s",
            exc,
        )
