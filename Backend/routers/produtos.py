# tdai_project/Backend/routers/produtos.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

import crud
import models
import schemas 
from database import get_db

from .auth_utils import get_current_active_user, get_current_active_superuser

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
    dependencies=[Depends(get_current_active_user)]
)

@router.post("/", response_model=schemas.Produto, status_code=status.HTTP_201_CREATED)
def create_new_produto(
    produto: schemas.ProdutoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if produto.fornecedor_id:
        db_fornecedor = crud.get_fornecedor(db, fornecedor_id=produto.fornecedor_id)
        if not db_fornecedor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fornecedor com id {produto.fornecedor_id} não encontrado.")
        if db_fornecedor.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a associar este produto ao fornecedor especificado.")
            
    return crud.create_produto(db=db, produto=produto, user_id=current_user.id)

@router.get("/", response_model=schemas.ProdutoPage) 
def read_user_produtos(
    skip: int = Query(0, ge=0, description="Número de itens a pular (offset)"),
    limit: int = Query(10, ge=1, le=200, description="Número máximo de itens a retornar"),
    fornecedor_id: Optional[int] = Query(None, description="Filtrar produtos por ID do fornecedor"),
    status_enriquecimento: Optional[models.StatusEnriquecimentoEnum] = Query(None, description="Filtrar produtos por status de enriquecimento web"),
    termo_busca: Optional[str] = Query(None, description="Termo para buscar em nome_base, marca ou categoria_original do produto"),
    # NOVOS PARÂMETROS DE QUERY PARA STATUS IA:
    status_titulo_ia: Optional[models.StatusGeracaoIAEnum] = Query(None, description="Filtrar por status da geração de títulos por IA."),
    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = Query(None, description="Filtrar por status da geração de descrição por IA."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    total_items = crud.count_produtos_by_user(
        db,
        user_id=current_user.id,
        fornecedor_id=fornecedor_id,
        status_enriquecimento=status_enriquecimento,
        termo_busca=termo_busca,
        # Passando os novos status para a contagem
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia
    )

    produtos_data = crud.get_produtos_by_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        fornecedor_id=fornecedor_id,
        status_enriquecimento=status_enriquecimento,
        termo_busca=termo_busca,
        # Passando os novos status para a busca
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia
    )
    return schemas.ProdutoPage(items=produtos_data, total_items=total_items, limit=limit, skip=skip)

@router.get("/{produto_id}", response_model=schemas.Produto)
def read_produto_details(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    
    if db_produto.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para acessar este produto")
    return db_produto

@router.put("/{produto_id}", response_model=schemas.Produto)
def update_existing_produto(
    produto_id: int,
    produto_update: schemas.ProdutoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    
    if db_produto.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para atualizar este produto")
    
    if produto_update.fornecedor_id is not None and produto_update.fornecedor_id != db_produto.fornecedor_id:
        new_fornecedor = crud.get_fornecedor(db, fornecedor_id=produto_update.fornecedor_id)
        if not new_fornecedor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Novo Fornecedor com id {produto_update.fornecedor_id} não encontrado.")
        if new_fornecedor.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a associar este produto ao novo fornecedor especificado.")
                
    updated_produto = crud.update_produto(db=db, db_produto=db_produto, produto_update=produto_update)
    return updated_produto

@router.delete("/{produto_id}", response_model=schemas.Produto)
def delete_existing_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    
    if db_produto.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para deletar este produto")
        
    deleted_produto = crud.delete_produto(db=db, db_produto=db_produto)
    return deleted_produto