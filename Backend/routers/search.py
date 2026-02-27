from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.database import get_db
from . import auth_utils

router = APIRouter(
    prefix="/search",
    tags=["Search"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)


class _SearchWorkflow:
    def search_all(
        self,
        db: Session,
        current_user: models.User,
        q: Optional[str],
        limit: int,
    ) -> schemas.SearchResults:
        results_items: List[Tuple] = []
        term = f"%{q.lower()}%" if q else None

        prod_query = db.query(
            models.Produto.id,
            models.Produto.nome_base,
            models.Produto.created_at,
        )
        if term:
            prod_query = prod_query.filter(func.lower(models.Produto.nome_base).ilike(term))
        if not current_user.is_superuser:
            prod_query = prod_query.filter(models.Produto.user_id == current_user.id)
        for prod in prod_query.order_by(models.Produto.created_at.desc()).limit(limit).all():
            results_items.append(
                (
                    prod.created_at,
                    schemas.SearchItem(id=prod.id, type="produto", name=prod.nome_base),
                )
            )

        forn_query = db.query(
            models.Fornecedor.id,
            models.Fornecedor.nome,
            models.Fornecedor.created_at,
        )
        if term:
            forn_query = forn_query.filter(func.lower(models.Fornecedor.nome).ilike(term))
        if not current_user.is_superuser:
            forn_query = forn_query.filter(models.Fornecedor.user_id == current_user.id)
        for forn in forn_query.order_by(models.Fornecedor.created_at.desc()).limit(limit).all():
            results_items.append(
                (
                    forn.created_at,
                    schemas.SearchItem(id=forn.id, type="fornecedor", name=forn.nome),
                )
            )

        pt_query = db.query(
            models.ProductType.id,
            models.ProductType.friendly_name,
            models.ProductType.created_at,
        )
        if term:
            pt_query = pt_query.filter(
                func.lower(models.ProductType.friendly_name).ilike(term)
            )
        if not current_user.is_superuser:
            pt_query = pt_query.filter(
                (models.ProductType.user_id == current_user.id)
                | (models.ProductType.user_id.is_(None))
            )
        for product_type in pt_query.order_by(models.ProductType.created_at.desc()).limit(limit).all():
            results_items.append(
                (
                    product_type.created_at,
                    schemas.SearchItem(
                        id=product_type.id,
                        type="tipo_produto",
                        name=product_type.friendly_name,
                    ),
                )
            )

        if current_user.is_superuser:
            user_query = db.query(models.User.id, models.User.email, models.User.created_at)
            if term:
                user_query = user_query.filter(func.lower(models.User.email).ilike(term))
            for user in user_query.order_by(models.User.created_at.desc()).limit(limit).all():
                results_items.append(
                    (
                        user.created_at,
                        schemas.SearchItem(id=user.id, type="usuario", name=user.email),
                    )
                )

        sorted_items = sorted(results_items, key=lambda item: item[0], reverse=True)
        results = [item for _, item in sorted_items][:limit]
        return schemas.SearchResults(results=results)


_search_workflow = _SearchWorkflow()


@router.get("/", response_model=schemas.SearchResults)
def search_all(
    q: Optional[str] = Query(None, min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return _search_workflow.search_all(
        db=db,
        current_user=current_user,
        q=q,
        limit=limit,
    )


class SearchRouterLegacyService:
    """Camada de compatibilidade para chamadas legadas do router."""

    def search_all(self, *args, **kwargs):
        return _search_workflow.search_all(*args, **kwargs)


search_router_legacy_service = SearchRouterLegacyService()
