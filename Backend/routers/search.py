from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from Backend.database import get_db
from Backend import models, schemas
from . import auth_utils

router = APIRouter(prefix="/search", tags=["Search"], dependencies=[Depends(auth_utils.get_current_active_user)])


@router.get("/", response_model=schemas.SearchResults)
def search_all(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    term = f"%{q.lower()}%"
    results: List[schemas.SearchItem] = []

    prod_query = db.query(models.Produto.id, models.Produto.nome_base).filter(func.lower(models.Produto.nome_base).ilike(term))
    if not current_user.is_superuser:
        prod_query = prod_query.filter(models.Produto.user_id == current_user.id)
    for prod in prod_query.limit(limit).all():
        results.append(schemas.SearchItem(id=prod.id, type="produto", name=prod.nome_base))

    forn_query = db.query(models.Fornecedor.id, models.Fornecedor.nome).filter(func.lower(models.Fornecedor.nome).ilike(term))
    if not current_user.is_superuser:
        forn_query = forn_query.filter(models.Fornecedor.user_id == current_user.id)
    for forn in forn_query.limit(limit).all():
        results.append(schemas.SearchItem(id=forn.id, type="fornecedor", name=forn.nome))

    pt_query = db.query(models.ProductType.id, models.ProductType.friendly_name).filter(func.lower(models.ProductType.friendly_name).ilike(term))
    if not current_user.is_superuser:
        pt_query = pt_query.filter((models.ProductType.user_id == current_user.id) | (models.ProductType.user_id.is_(None)))
    for pt in pt_query.limit(limit).all():
        results.append(schemas.SearchItem(id=pt.id, type="tipo_produto", name=pt.friendly_name))

    if current_user.is_superuser:
        user_query = db.query(models.User.id, models.User.email).filter(func.lower(models.User.email).ilike(term))
        for user in user_query.limit(limit).all():
            results.append(schemas.SearchItem(id=user.id, type="usuario", name=user.email))

    return {"results": results[:limit]}
