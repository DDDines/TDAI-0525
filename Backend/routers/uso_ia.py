# Backend/routers/uso_ia.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime # Necessário para filtros de data

import crud
import models
import schemas # schemas é importado
import database
from . import auth_utils # Para obter o usuário logado

router = APIRouter(
    prefix="/uso-ia", # FIX: Removido o '/api/v1' daqui
    tags=["uso-ia"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

# Endpoint para registrar um novo uso de IA
@router.post("/", response_model=schemas.RegistroUsoIAResponse, status_code=status.HTTP_201_CREATED) # CORRIGIDO AQUI
def create_uso_ia_endpoint( 
    uso_ia_data: schemas.RegistroUsoIACreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """
    Registra um novo uso de funcionalidade de IA pelo usuário.
    """
    try:
        # A função no CRUD foi nomeada como create_registro_uso_ia
        return crud.create_registro_uso_ia(db=db, uso_ia=uso_ia_data, user_id=current_user.id) 
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"ERRO INESPERADO ao criar registro de uso de IA: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao registrar uso de IA.")

# Endpoint para listar os registros de uso de IA para o usuário logado
@router.get("/", response_model=schemas.RegistroUsoIABase) 
def read_usos_ia_usuario_logado(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    skip: int = Query(0, ge=0, description="Número de itens para pular"),
    limit: int = Query(100, ge=1, le=200, description="Número máximo de itens por página"), 
    tipo_geracao: Optional[str] = Query(None, description="Filtrar por tipo de geração (ex: 'titulo_produto')"),
    data_inicio: Optional[datetime] = Query(None, description="Filtrar por data de início (YYYY-MM-DDTHH:MM:SS)"),
    data_fim: Optional[datetime] = Query(None, description="Filtrar por data de fim (YYYY-MM-DDTHH:MM:SS)")
):
    """
    Lista os registros de uso de IA para o usuário autenticado, com filtros e paginação.
    """
    # FIX: Change 'get_registros_uso_ia_by_user' to 'get_registros_uso_ia'
    registros = crud.get_registros_uso_ia( # Corrected function name
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        tipo_acao=tipo_geracao, # Changed from tipo_geracao to tipo_acao to match crud function
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    # FIX: Change 'count_registros_uso_ia_by_user' to 'count_registros_uso_ia'
    total_items = crud.count_registros_uso_ia( # Corrected function name
        db,
        user_id=current_user.id,
        tipo_acao=tipo_geracao, # Changed from tipo_geracao to tipo_acao to match crud function
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    return {"items": registros, "total_items": total_items, "page": skip // limit, "limit": limit}


# Endpoint para obter detalhes de um registro de uso de IA específico (se necessário)
@router.get("/{registro_id}", response_model=schemas.RegistroUsoIAResponse) 
def read_uso_ia_especifico( 
    registro_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Obtém detalhes de um registro de uso de IA específico,
    verificando se pertence ao usuário logado ou se o usuário é admin.
    """
    # Idealmente, crie esta função em crud.py:
    # def get_registro_uso_ia(db: Session, registro_id: int) -> Optional[models.RegistroUsoIA]:
    # return db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.id == registro_id).first()
    
    # Simulando a busca direta enquanto a função CRUD não existe:
    db_registro = db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.id == registro_id).first() 

    if db_registro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de uso de IA não encontrado.")
    
    if not current_user.is_superuser and db_registro.user_id != current_user.id: 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a visualizar este registro.")
        
    return db_registro


@router.get("/por-produto/{produto_id}", response_model=List[schemas.RegistroUsoIAResponse])
def read_usos_ia_por_produto(
    produto_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=200)
):
    """
    Lista os registros de uso de IA para um produto específico.
    Verifica se o produto pertence ao usuário ou se o usuário é admin.
    """
    # Primeiro, verifica o acesso ao produto
    produto = crud.get_produto(db, produto_id=produto_id) 
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if not current_user.is_superuser and produto.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver usos de IA para este produto")
        
    # A função no CRUD foi nomeada como get_usos_ia_by_produto
    usos = crud.get_usos_ia_by_produto(db, produto_id=produto_id, user_id=current_user.id, skip=skip, limit=limit)
    return usos
