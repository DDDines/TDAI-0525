"""Authenticated dashboard endpoints for the current user."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.admin_analytics_repository import (
    AdminAnalyticsRepository,
)
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository

from . import auth_utils

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


def _resolve_user_limit(current_user: models.User, field_name: str, fallback: int = 0) -> int:
    """Resolve one limit preferring explicit user values and falling back to the plan."""
    explicit_value = getattr(current_user, field_name, None)
    if explicit_value is not None:
        return int(explicit_value)
    plano = getattr(current_user, "plano", None)
    plano_value = getattr(plano, field_name, None) if plano is not None else None
    return int(plano_value or fallback or 0)


@router.get("/me", response_model=schemas.DashboardMeResponse)
def read_my_dashboard(
    current_user: models.User = Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Return the authenticated user's operational dashboard payload."""
    analytics_repo = AdminAnalyticsRepository(session)
    historico_repo = HistoricoRepository(session)
    fornecedor_repo = FornecedorRepository(session)

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    plano_nome = str(getattr(getattr(current_user, "plano", None), "nome", "") or "Gratuito")

    status_counts = [
        schemas.ProductStatusCount(status=status, total=total)
        for status, total in analytics_repo.list_product_status_counts_by_user(user_id=current_user.id)
        if status is not None
    ]
    atividade_recente = historico_repo.get_registros_historico(
        user_id=current_user.id,
        skip=0,
        limit=6,
    )

    return schemas.DashboardMeResponse(
        plano_nome=plano_nome,
        product_experience_mode=current_user.product_experience_mode,
        limites={
            "produtos": _resolve_user_limit(current_user, "limite_produtos"),
            "enriquecimento_web": _resolve_user_limit(current_user, "limite_enriquecimento_web"),
            "geracao_ia": _resolve_user_limit(current_user, "limite_geracao_ia"),
        },
        uso_mes_atual={
            "geracao_ia": analytics_repo.count_ia_usage_by_user_since(
                user_id=current_user.id,
                start_at=month_start,
            ),
            "enriquecimento_web": analytics_repo.count_web_enrichment_usage_by_user_since(
                user_id=current_user.id,
                start_at=month_start,
            ),
        },
        totais={
            "produtos": analytics_repo.count_products_by_user(user_id=current_user.id),
            "fornecedores": fornecedor_repo.count_fornecedores_by_user(
                user_id=current_user.id,
                is_admin=current_user.is_superuser,
                search=None,
            ),
        },
        status_produtos=status_counts,
        atividade_recente=atividade_recente,
        atalhos=[
            schemas.DashboardShortcut(
                label="Produtos",
                description="Gerencie seu catalogo e acompanhe geracoes.",
                route="/produtos",
            ),
            schemas.DashboardShortcut(
                label="Enriquecimento",
                description="Revise itens enriquecidos e rode novas coletas.",
                route="/enriquecimento",
            ),
            schemas.DashboardShortcut(
                label="Historico",
                description="Acompanhe a atividade recente da sua conta.",
                route="/historico",
            ),
            schemas.DashboardShortcut(
                label="Configuracoes",
                description="Ajuste plano, credenciais e preferencias.",
                route="/configuracoes",
            ),
        ],
    )
