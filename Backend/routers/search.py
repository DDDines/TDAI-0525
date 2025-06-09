from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from Backend.database import get_db
from Backend import models, schemas
from . import auth_utils

router = APIRouter(prefix="/search", tags=["Search"], dependencies=[Depends(auth_utils.get_current_active_user)])


@router.get("/", response_model=schemas.SearchResults)
def search_all(
    q: Optional[str] = Query(None, min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    results_items: List[Tuple] = []

    prod_query = db.query(models.Produto.id, models.Produto.nome_base, models.Produto.created_at)
    if q:
        term = f"%{q.lower()}%"
        prod_query = prod_query.filter(func.lower(models.Produto.nome_base).ilike(term))
    if not current_user.is_superuser:
        prod_query = prod_query.filter(models.Produto.user_id == current_user.id)
    prod_query = prod_query.order_by(models.Produto.created_at.desc())
    for prod in prod_query.limit(limit).all():
        results_items.append((prod.created_at, schemas.SearchItem(id=prod.id, type="produto", name=prod.nome_base)))

    forn_query = db.query(models.Fornecedor.id, models.Fornecedor.nome, models.Fornecedor.created_at)
    if q:
        forn_query = forn_query.filter(func.lower(models.Fornecedor.nome).ilike(term))
    if not current_user.is_superuser:
        forn_query = forn_query.filter(models.Fornecedor.user_id == current_user.id)
    forn_query = forn_query.order_by(models.Fornecedor.created_at.desc())
    for forn in forn_query.limit(limit).all():
        results_items.append((forn.created_at, schemas.SearchItem(id=forn.id, type="fornecedor", name=forn.nome)))

    pt_query = db.query(models.ProductType.id, models.ProductType.friendly_name, models.ProductType.created_at)
    if q:
        pt_query = pt_query.filter(func.lower(models.ProductType.friendly_name).ilike(term))
    if not current_user.is_superuser:
        pt_query = pt_query.filter((models.ProductType.user_id == current_user.id) | (models.ProductType.user_id.is_(None)))
    pt_query = pt_query.order_by(models.ProductType.created_at.desc())
    for pt in pt_query.limit(limit).all():
        results_items.append((pt.created_at, schemas.SearchItem(id=pt.id, type="tipo_produto", name=pt.friendly_name)))

    if current_user.is_superuser:
        user_query = db.query(models.User.id, models.User.email, models.User.created_at)
        if q:
            user_query = user_query.filter(func.lower(models.User.email).ilike(term))
        user_query = user_query.order_by(models.User.created_at.desc())
        for user in user_query.limit(limit).all():
            results_items.append((user.created_at, schemas.SearchItem(id=user.id, type="usuario", name=user.email)))

    if q:
        # When searching, simply return the combined results limited by `limit`
        results = [item[1] for item in results_items][:limit]
    else:
        # Sort all items by creation date and take the most recent ones
        results = [item for _, item in sorted(results_items, key=lambda x: x[0], reverse=True)][:limit]

    return {"results": results}
