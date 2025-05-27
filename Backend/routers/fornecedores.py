# tdai_project/Backend/routers/fornecedores.py
from fastapi import APIRouter, Depends, HTTPException, status, Query # Adicionado Query
from sqlalchemy.orm import Session
from typing import List, Optional

import crud 
import models 
import schemas 
from database import get_db 

from .auth_utils import get_current_active_user, get_current_active_superuser

router = APIRouter(
    prefix="/fornecedores",
    tags=["Fornecedores"],
    dependencies=[Depends(get_current_active_user)]
)

@router.post("/", response_model=schemas.Fornecedor, status_code=status.HTTP_201_CREATED)
def create_new_fornecedor(
    fornecedor: schemas.FornecedorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return crud.create_fornecedor(db=db, fornecedor=fornecedor, user_id=current_user.id)

@router.get("/", response_model=schemas.FornecedorPage) # Alterado para o novo schema de paginação
def read_user_fornecedores(
    skip: int = Query(0, ge=0, description="Número de itens a pular"),
    limit: int = Query(10, ge=1, le=200, description="Número máximo de itens a retornar"), # Default limit para 10
    termo_busca: Optional[str] = Query(None, description="Termo para buscar no nome do fornecedor"), # Adicionado termo_busca
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    total_items = crud.count_fornecedores_by_user(
        db, 
        user_id=current_user.id,
        termo_busca=termo_busca
    )
    fornecedores_data = crud.get_fornecedores_by_user(
        db, 
        user_id=current_user.id, 
        skip=skip, 
        limit=limit,
        termo_busca=termo_busca
    )
    return schemas.FornecedorPage(items=fornecedores_data, total_items=total_items, limit=limit, skip=skip)

@router.get("/{fornecedor_id}", response_model=schemas.Fornecedor)
def read_fornecedor_details(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id)
    if db_fornecedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado")
    
    if db_fornecedor.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para acessar este fornecedor")
    return db_fornecedor

@router.put("/{fornecedor_id}", response_model=schemas.Fornecedor)
def update_existing_fornecedor(
    fornecedor_id: int,
    fornecedor_update: schemas.FornecedorUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id)
    if db_fornecedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado")
    
    if db_fornecedor.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para atualizar este fornecedor")
    
    # Verifica se já existe outro fornecedor com o mesmo nome para o usuário atual
    if fornecedor_update.nome and fornecedor_update.nome != db_fornecedor.nome:
        outro_fornecedor_com_mesmo_nome = db.query(models.Fornecedor).filter(
            models.Fornecedor.nome == fornecedor_update.nome,
            models.Fornecedor.user_id == current_user.id,
            models.Fornecedor.id != fornecedor_id # Exclui o próprio fornecedor da verificação
        ).first()
        if outro_fornecedor_com_mesmo_nome:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Outro fornecedor com o nome '{fornecedor_update.nome}' já existe.")

    updated_fornecedor = crud.update_fornecedor(db=db, db_fornecedor=db_fornecedor, fornecedor_update=fornecedor_update)
    return updated_fornecedor

@router.delete("/{fornecedor_id}", response_model=schemas.Fornecedor)
def delete_existing_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_fornecedor = crud.get_fornecedor(db, fornecedor_id=fornecedor_id)
    if db_fornecedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado")
    
    if db_fornecedor.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para deletar este fornecedor")
    
    produtos_associados = db.query(models.Produto).filter(models.Produto.fornecedor_id == fornecedor_id).first()
    if produtos_associados:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível deletar o fornecedor. Existem produtos associados a ele. Remova ou desassocie os produtos primeiro."
        )

    deleted_fornecedor = crud.delete_fornecedor(db=db, db_fornecedor=db_fornecedor)
    return deleted_fornecedor