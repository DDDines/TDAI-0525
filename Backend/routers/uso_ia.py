# Backend/routers/uso_ia.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime # Necessário para filtros de data

from Backend import crud
from Backend import crud_produtos
from Backend import models
from Backend import schemas  # schemas é importado
from Backend import database
from . import auth_utils # Para obter o usuário logado
from Backend.core.logging_config import get_logger

router = APIRouter(
    prefix="/uso-ia", # FIX: Removido o '/api/v1' daqui
    tags=["uso-ia"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

logger = get_logger(__name__)

# Endpoint para registrar um novo uso de IA
@router.post("/", response_model=schemas.RegistroUsoIAResponse, status_code=status.HTTP_201_CREATED)  # CORRIGIDO AQUI
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
        uso_ia_data.user_id = current_user.id
        return crud.create_registro_uso_ia(db, registro_uso=uso_ia_data)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("ERRO INESPERADO ao criar registro de uso de IA: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao registrar uso de IA.")

# Endpoint para listar os registros de uso de IA para o usuário logado
@router.get("/", response_model=schemas.UsoIAPage)
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
    try:
        tipo_enum = models.TipoAcaoEnum(tipo_geracao) if tipo_geracao else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="tipo_geracao inválido")

    registros = crud.get_registros_uso_ia(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        tipo_acao=tipo_enum,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    # FIX: Change 'count_registros_uso_ia_by_user' to 'count_registros_uso_ia'
    total_items = crud.count_registros_uso_ia(
        db,
        user_id=current_user.id,
        tipo_acao=tipo_enum,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    page_number = skip // limit + 1
    return {
        "items": registros,
        "total_items": total_items,
        "page": page_number,
        "limit": limit,
    }


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
    produto = crud_produtos.get_produto(db, produto_id=produto_id) 
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if not current_user.is_superuser and produto.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver usos de IA para este produto")
        
    # A função no CRUD foi nomeada como get_usos_ia_by_produto
    query_user_id = produto.user_id if current_user.is_superuser else current_user.id
    usos = crud.get_usos_ia_by_produto(
        db,
        produto_id=produto_id,
        user_id=query_user_id,
        skip=skip,
        limit=limit,
    )
    return usos
