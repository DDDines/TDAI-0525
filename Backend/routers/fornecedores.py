# Backend/routers/fornecedores.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

import schemas
import models
import crud # Contém get_fornecedor, get_fornecedores, create_fornecedor, etc.
from database import get_db
from routers import auth_utils # Para get_current_active_user

router = APIRouter(
    prefix="/fornecedores", # O /api/v1 é adicionado no main.py
    tags=["Fornecedores"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Fornecedor, status_code=status.HTTP_201_CREATED)
def create_user_fornecedor(
    fornecedor: schemas.FornecedorCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # O user_id é pego do current_user, não precisa estar no schema FornecedorCreate
    return crud.create_fornecedor(db=db, fornecedor=fornecedor, user_id=current_user.id)

@router.get("/", response_model=schemas.FornecedorPage) # response_model espera items e total_items
def read_user_fornecedores(
    skip: int = Query(0, ge=0), 
    limit: int = Query(10, ge=1, le=100), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # Primeiro, fazemos a query para obter os itens da página atual
    fornecedores_items = crud.get_fornecedores(db, user_id=current_user.id, skip=skip, limit=limit)
    
    # Depois, fazemos uma query separada para contar o total de itens para este usuário
    # Esta é a parte que estava faltando ou causando o erro.
    # A query base para contagem deve ser a mesma da busca de itens, antes do offset/limit.
    query_base_para_contagem = db.query(models.Fornecedor).filter(models.Fornecedor.user_id == current_user.id)
    total_items = query_base_para_contagem.count()
    
    return schemas.FornecedorPage(
        items=fornecedores_items,
        total_items=total_items,
        limit=limit,
        skip=skip
    )

@router.get("/all", response_model=List[schemas.Fornecedor], dependencies=[Depends(auth_utils.get_current_active_superuser)])
def read_all_fornecedores_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    """
    Endpoint para administradores listarem todos os fornecedores de todos os usuários.
    """
    return crud.get_all_fornecedores_admin(db, skip=skip, limit=limit)


@router.get("/{fornecedor_id}", response_model=schemas.Fornecedor)
def read_user_fornecedor(
    fornecedor_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id, user_id=current_user.id)
    if db_fornecedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado ou não pertence ao usuário")
    return db_fornecedor

@router.put("/{fornecedor_id}", response_model=schemas.Fornecedor)
def update_user_fornecedor(
    fornecedor_id: int, 
    fornecedor_update: schemas.FornecedorUpdate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id, user_id=current_user.id)
    if db_fornecedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Fornecedor não encontrado ou não pertence ao usuário para atualização"
        )
    return crud.update_fornecedor(db=db, db_fornecedor=db_fornecedor, fornecedor_update=fornecedor_update)

@router.delete("/{fornecedor_id}", response_model=schemas.Msg)
def delete_user_fornecedor(
    fornecedor_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id, user_id=current_user.id)
    if db_fornecedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Fornecedor não encontrado ou não pertence ao usuário para deleção"
        )
    
    # Verificar se há produtos associados a este fornecedor
    if db_fornecedor.produtos: # Se a relação 'produtos' em Fornecedor estiver carregada ou for consultável
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível deletar o fornecedor '{db_fornecedor.nome}' pois ele possui produtos associados. Por favor, desassocie ou delete os produtos primeiro."
        )
        
    crud.delete_fornecedor(db=db, db_fornecedor=db_fornecedor)
    return {"message": f"Fornecedor {fornecedor_id} ('{db_fornecedor.nome}') deletado com sucesso."}