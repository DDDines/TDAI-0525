# Backend/routers/product_types.py
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Path as FastAPIPath, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from Backend import crud_product_types
from Backend import models
from Backend import schemas
from Backend import database
from . import auth_utils
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)

from Backend.core.config import logger

router = APIRouter(
    prefix="/product-types", 
    tags=["Tipos de Produto e Templates de Atributos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

@router.post("/", response_model=schemas.ProductTypeResponse, status_code=status.HTTP_201_CREATED)
def create_product_type_endpoint( 
    product_type_in: schemas.ProductTypeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    user_id_for_type = None if current_user.is_superuser else current_user.id
    logger.info()
    logger.debug(
        "ROUTER (create_product_type): Verificando existência de key_name '%s' para user_id: %s",
        product_type_in.key_name,
        user_id_for_type,
    )
    existing_type = crud_product_types.get_product_type_by_key_name(db, key_name=product_type_in.key_name, user_id=user_id_for_type)
    
    if user_id_for_type is None and not existing_type: 
        existing_type_global_check = crud_product_types.get_product_type_by_key_name(db, key_name=product_type_in.key_name, user_id=None)
        if existing_type_global_check:
             existing_type = existing_type_global_check

    if existing_type:
        scope_msg = "globalmente" if existing_type.user_id is None else f"para o usuário ID {existing_type.user_id}"
        logger.warning()
        logger.info(
            "ROUTER (create_product_type): Conflito! Tipo com key_name '%s' já existe %s.",
            product_type_in.key_name,
            scope_msg,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Um tipo de produto com a chave '{product_type_in.key_name}' já existe {scope_msg}."
        )
        
    logger.info(
        "ROUTER (create_product_type): Criando tipo de produto '%s' com key_name '%s' para user_id: %s",
        product_type_in.friendly_name,
        product_type_in.key_name,
        user_id_for_type,
    )
    return crud_product_types.create_product_type(db=db, product_type_create=product_type_in, user_id=user_id_for_type)


@router.get("/", response_model=List[schemas.ProductTypeResponse])
def read_product_types_endpoint( 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    logger.info()
    logger.debug(
        "ROUTER (read_product_types): Buscando tipos de produto para user_id: %s, skip: %s, limit: %s",
        current_user.id,
        skip,
        limit,
    )
    product_types = crud_product_types.get_product_types_for_user(db, skip=skip, limit=limit, user_id=current_user.id)
    logger.info(
        "ROUTER (read_product_types): Encontrados %s tipos de produto.",
        len(product_types),
    )

    logger.debug(
        "ROUTER (read_product_types): Encontrados %s tipos de produto.", len(product_types)
    )
    return product_types

@router.get("/{type_id_or_key_path:path}", response_model=schemas.ProductTypeResponse, name="read_product_type_details")
async def read_product_type_details_route(
    type_id_or_key_path: str = FastAPIPath(..., description="ID (numérico) ou KeyName (string) do Tipo de Produto"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    identifier = type_id_or_key_path 
    logger.info("ROUTER (read_product_type_details): Iniciando busca por '%s'", identifier)
    logger.debug(
        "ROUTER (read_product_type_details): Iniciando busca por '%s'",
        identifier,
    )
    db_product_type = None
    
    try:
        numeric_id = int(identifier)
        logger.info("ROUTER: Identificador '%s' é numérico. Tentando buscar por ID: %s", identifier, numeric_id)
        db_product_type = crud_product_types.get_product_type(db, product_type_id=numeric_id)
        if db_product_type:
            logger.info()
        logger.debug(
            "ROUTER: Identificador '%s' é numérico. Tentando buscar por ID: %s",
            identifier,
            numeric_id,
        )
        db_product_type = crud_product_types.get_product_type(db, product_type_id=numeric_id) 
        if db_product_type:
            logger.debug(

                "ROUTER: Encontrado por ID: %s - %s",
                db_product_type.id,
                db_product_type.friendly_name,
            )
    except ValueError:
        logger.info(
            "ROUTER: Identificador '%s' não é puramente numérico. Será tratado como key_name.",
            identifier,
        )
        pass

    if not db_product_type: 
        key_name_to_search = str(identifier)
        logger.info()
        logger.debug(
            "ROUTER: Identificador '%s' não é puramente numérico. Será tratado como key_name.",
            identifier,
        )
        pass 

    if not db_product_type: 
        key_name_to_search = str(identifier) 
        logger.debug(
            "ROUTER: Não encontrado por ID (ou não era ID numérico válido). Tentando buscar por key_name: '%s' para user_id: %s (específico)",
            key_name_to_search,
            current_user.id,
        )
        db_product_type = crud_product_types.get_product_type_by_key_name(db, key_name=key_name_to_search, user_id=current_user.id)
        
        if not db_product_type:
            logger.info()

            logger.debug(
                "ROUTER: Não encontrado como tipo do usuário. Tentando buscar globalmente por key_name: '%s' (user_id: None)",
                key_name_to_search,
            )
            db_product_type = crud_product_types.get_product_type_by_key_name(db, key_name=key_name_to_search, user_id=None)

    if db_product_type is None:
        logger.info(
            "ROUTER: Tipo de produto NÃO encontrado para identificador '%s' após todas as tentativas.",
            identifier,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tipo de Produto com identificador '{identifier}' não encontrado.")
    
    is_global = db_product_type.user_id is None
    is_owner = db_product_type.user_id == current_user.id

    if not (current_user.is_superuser or is_global or is_owner):
        logger.warning(
            "ROUTER: Permissão NEGADA para usuário ID %s acessar tipo de produto ID %s (Owner: %s, Global: %s)",
            current_user.id,
            db_product_type.id,
            db_product_type.user_id,
            is_global,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a visualizar este tipo de produto.")
    

    logger.info()

    logger.debug(

        "ROUTER: Permissão CONCEDIDA. Retornando tipo de produto ID %s ('%s')",
        db_product_type.id,
        db_product_type.friendly_name,
    )
    return db_product_type


@router.put("/{type_id}", response_model=schemas.ProductTypeResponse)
def update_product_type_endpoint( 
    type_id: int, 
    product_type_in: schemas.ProductTypeUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):

    logger.info()
    logger.debug(
        "ROUTER (update_product_type): Tentando atualizar tipo de produto ID %s para usuário ID %s",
        type_id,
        current_user.id,
    )
    db_product_type = crud_product_types.get_product_type(db, type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de produto não encontrado.")

    updated_type = crud_product_types.update_product_type(db=db, db_product_type=db_product_type, product_type_update=product_type_in)

    logger.info("ROUTER (update_product_type): Tipo de produto ID %s atualizado com sucesso.", type_id)

    logger.info(
        "ROUTER (update_product_type): Tipo de produto ID %s atualizado com sucesso.",
        type_id,
    )
    return updated_type

@router.delete("/{type_id}", response_model=schemas.ProductTypeResponse) 
def delete_product_type_endpoint( 
    type_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    logger.info()

    logger.debug(
        "ROUTER (delete_product_type): Tentando deletar tipo de produto ID %s para usuário ID %s",
        type_id,
        current_user.id,
    )
    db_product_type = crud_product_types.get_product_type(db, type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado para deleção.")

    deleted_type = crud_product_types.delete_product_type(db=db, db_product_type=db_product_type)

    logger.info("ROUTER (delete_product_type): Tipo de produto ID %s deletado com sucesso.", type_id)

    logger.info(
        "ROUTER (delete_product_type): Tipo de produto ID %s deletado com sucesso.",
        type_id,
    )
    return deleted_type

@router.post("/{type_id}/attributes/", response_model=schemas.AttributeTemplateResponse, status_code=status.HTTP_201_CREATED)
def add_attribute_to_product_type_endpoint( 
    type_id: int,
    attribute_in: schemas.AttributeTemplateCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):

    logger.info()

    logger.debug(

        "ROUTER (add_attribute): Tentando adicionar atributo ao tipo ID %s para usuário ID %s",
        type_id,
        current_user.id,
    )
    existing_attr_template = db.query(models.AttributeTemplate).filter(
        models.AttributeTemplate.product_type_id == type_id,
        models.AttributeTemplate.attribute_key == attribute_in.attribute_key
    ).first()
    if existing_attr_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Um atributo com a chave '{attribute_in.attribute_key}' já existe para este tipo de produto."
        )
    
    new_attribute = crud_product_types.create_attribute_template(db=db, attribute_template_data=attribute_in, product_type_id=type_id, user_id=current_user.id)
    logger.info(
        "ROUTER (add_attribute): Atributo '%s' adicionado ao tipo ID %s.",
        new_attribute.label,
        type_id,
    )
    return new_attribute

@router.put("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def update_attribute_for_product_type_endpoint( 
    type_id: int, 
    attribute_id: int,
    attribute_in: schemas.AttributeTemplateUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):

    logger.info()

    logger.debug(

        "ROUTER (update_attribute): Tentando atualizar atributo ID %s do tipo ID %s para usuário ID %s",
        attribute_id,
        type_id,
        current_user.id,
    )
    db_attribute_to_check = crud_product_types.get_attribute_template(db, attribute_id)
    if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo não encontrado ou não pertence ao tipo de produto especificado.")

    if attribute_in.attribute_key and attribute_in.attribute_key != db_attribute_to_check.attribute_key:
        existing_attr_with_new_key = db.query(models.AttributeTemplate).filter(
            models.AttributeTemplate.product_type_id == type_id,
            models.AttributeTemplate.attribute_key == attribute_in.attribute_key,
            models.AttributeTemplate.id != attribute_id 
        ).first()
        if existing_attr_with_new_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Um atributo com a nova chave '{attribute_in.attribute_key}' já existe para este tipo de produto."
            )

    updated_attribute = crud_product_types.update_attribute_template(db=db, attribute_template_id=attribute_id, attribute_template_data=attribute_in, user_id=current_user.id)
    if not updated_attribute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao atualizar o atributo.")

    logger.info("ROUTER (update_attribute): Atributo ID %s atualizado.", attribute_id)

    logger.info(
        "ROUTER (update_attribute): Atributo ID %s atualizado.",
        attribute_id,
    )
    return updated_attribute

@router.delete("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def remove_attribute_from_product_type_endpoint( 
    type_id: int, 
    attribute_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):

    logger.info()

    logger.debug(
        "ROUTER (delete_attribute): Tentando deletar atributo ID %s do tipo ID %s para usuário ID %s",
        attribute_id,
        type_id,
        current_user.id,
    )
    db_attribute_to_check = crud_product_types.get_attribute_template(db, attribute_id)
    if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo não encontrado ou não pertence ao tipo de produto especificado para deleção.")

    deleted_attribute = crud_product_types.delete_attribute_template(db=db, attribute_template_id=attribute_id, user_id=current_user.id)
    if not deleted_attribute: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao deletar o atributo.")

    logger.info("ROUTER (delete_attribute): Atributo ID %s deletado.", attribute_id)

    logger.info(
        "ROUTER (delete_attribute): Atributo ID %s deletado.",
        attribute_id,
    )

    return deleted_attribute

# --- NOVO ENDPOINT PARA REORDENAR ---
class ReorderRequest(BaseModel):
    direction: str # "up" ou "down"

@router.post("/{type_id}/attributes/{attribute_id}/reorder", response_model=schemas.AttributeTemplateResponse)
def reorder_attribute_endpoint(
    type_id: int,
    attribute_id: int,
    reorder_request: ReorderRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # Primeiro, verificação de permissão no tipo de produto
    product_type = crud_product_types.get_product_type(db, type_id)
    if not product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de produto não encontrado.")
    
    is_owner = product_type.user_id == current_user.id
    if not current_user.is_superuser and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a modificar este tipo de produto.")
    
    # Chama a nova função do CRUD
    reordered_attribute = crud_product_types.reorder_attribute_template(db, attribute_id=attribute_id, direction=reorder_request.direction)
    
    if not reordered_attribute:
        # A função CRUD pode retornar None se o atributo não for encontrado ou se o movimento for impossível
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo não encontrado ou movimento inválido.")
        
    return reordered_attribute
