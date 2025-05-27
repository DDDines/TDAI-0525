# tdai_project/Backend/routers/uso_ia.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

import crud
import models
import schemas # Certifique-se que schemas está importado para usar schemas.UsoIAPage
from database import get_db

from .auth_utils import get_current_active_user, get_current_active_superuser

router = APIRouter(
    prefix="/uso-ia",
    tags=["Uso IA (Histórico e Limites)"],
    dependencies=[Depends(get_current_active_user)]
)

@router.post("/", response_model=schemas.UsoIA, status_code=status.HTTP_201_CREATED)
def registrar_novo_uso_ia(
    uso_ia_data: schemas.UsoIACreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if uso_ia_data.produto_id:
        produto = crud.get_produto(db, produto_id=uso_ia_data.produto_id)
        if not produto:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Produto com id {uso_ia_data.produto_id} não encontrado.")
        if produto.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Não autorizado a registrar uso para o produto id {uso_ia_data.produto_id} de outro usuário.")

    return crud.create_uso_ia(db=db, uso_ia=uso_ia_data, user_id=current_user.id)


@router.get("/me/", response_model=schemas.UsoIAPage, summary="Meu Histórico de Uso da IA") # Response model ALTERADO
def ler_meu_historico_uso_ia(
    skip: int = Query(0, ge=0),
    limit: int = Query(15, ge=1, le=200), # Limite padrão ajustado para 15
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    total_items = crud.count_usos_ia_by_user(db, user_id=current_user.id) # BUSCA TOTAL
    items = crud.get_usos_ia_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return schemas.UsoIAPage(items=items, total_items=total_items, limit=limit, skip=skip) # RETORNA OBJETO PAGINADO

@router.get("/produto/{produto_id}/", response_model=List[schemas.UsoIA], summary="Histórico de Uso da IA por Produto")
def ler_historico_uso_ia_por_produto(
    produto_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    usos = crud.get_usos_ia_by_produto(db, produto_id=produto_id, user_id=current_user.id, skip=skip, limit=limit)

    if not usos:
        produto_check = crud.get_produto(db, produto_id=produto_id)
        if not produto_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.")
        # Se o produto existe mas não tem histórico, retorna lista vazia (comportamento ok)

    return usos

@router.get("/all/", response_model=List[schemas.UsoIA], dependencies=[Depends(get_current_active_superuser)], summary="[Admin] Todo Histórico de Uso da IA")
def ler_todo_historico_uso_ia(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    user_id_filter: Optional[int] = Query(None, description="[Admin] Filtrar por ID de usuário específico"),
    db: Session = Depends(get_db)
):
    if user_id_filter:
        # Nota: Para paginação completa aqui também, precisaria de count_usos_ia_by_user e retornar UsoIAPage
        return crud.get_usos_ia_by_user(db, user_id=user_id_filter, skip=skip, limit=limit)
    else:
        # Nota: Para paginação completa aqui também, precisaria de uma função count_all_usos_ia e retornar UsoIAPage
        return db.query(models.UsoIA).order_by(models.UsoIA.timestamp.desc()).offset(skip).limit(limit).all()