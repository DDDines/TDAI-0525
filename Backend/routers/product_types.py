# Backend/routers/product_types.py
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Path as FastAPIPath
from sqlalchemy.orm import Session

import crud
import models
import schemas
import database 
from . import auth_utils 

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
    
    print(f"ROUTER (create_product_type): Verificando existência de key_name '{product_type_in.key_name}' para user_id: {user_id_for_type}")
    existing_type = crud.get_product_type_by_key_name(db, key_name=product_type_in.key_name, user_id=user_id_for_type)
    
    if user_id_for_type is None and not existing_type: 
        existing_type_global_check = crud.get_product_type_by_key_name(db, key_name=product_type_in.key_name, user_id=None)
        if existing_type_global_check:
             existing_type = existing_type_global_check

    if existing_type:
        scope_msg = "globalmente" if existing_type.user_id is None else f"para o usuário ID {existing_type.user_id}"
        print(f"ROUTER (create_product_type): Conflito! Tipo com key_name '{product_type_in.key_name}' já existe {scope_msg}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Um tipo de produto com a chave '{product_type_in.key_name}' já existe {scope_msg}."
        )
        
    print(f"ROUTER (create_product_type): Criando tipo de produto '{product_type_in.friendly_name}' com key_name '{product_type_in.key_name}' para user_id: {user_id_for_type}")
    return crud.create_product_type(db=db, product_type_data=product_type_in, user_id=user_id_for_type)


@router.get("/", response_model=List[schemas.ProductTypeResponse])
def read_product_types_endpoint( 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    print(f"ROUTER (read_product_types): Buscando tipos de produto para user_id: {current_user.id}, skip: {skip}, limit: {limit}")
    product_types = crud.get_product_types(db, skip=skip, limit=limit, user_id=current_user.id)
    print(f"ROUTER (read_product_types): Encontrados {len(product_types)} tipos de produto.")
    return product_types

# --- ESTA É A ROTA CRÍTICA PARA O ERRO 404 ---
@router.get("/{type_id_or_key_path:path}", response_model=schemas.ProductTypeResponse, name="read_product_type_details")
async def read_product_type_details_route(
    type_id_or_key_path: str = FastAPIPath(..., description="ID (numérico) ou KeyName (string) do Tipo de Produto"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    identifier = type_id_or_key_path 
    print(f"ROUTER (read_product_type_details): Iniciando busca por '{identifier}'") 
    db_product_type = None
    
    try:
        numeric_id = int(identifier)
        print(f"ROUTER: Identificador '{identifier}' é numérico. Tentando buscar por ID: {numeric_id}") 
        # Chama crud.get_product_type que busca por ID e já tem logs de debug
        db_product_type = crud.get_product_type(db, product_type_id=numeric_id) 
        if db_product_type:
            print(f"ROUTER: Encontrado por ID: {db_product_type.id} - {db_product_type.friendly_name}") 
    except ValueError:
        print(f"ROUTER: Identificador '{identifier}' não é puramente numérico. Será tratado como key_name.")
        pass 

    if not db_product_type: 
        key_name_to_search = str(identifier) 
        print(f"ROUTER: Não encontrado por ID (ou não era ID numérico válido). Tentando buscar por key_name: '{key_name_to_search}' para user_id: {current_user.id} (específico)") 
        db_product_type = crud.get_product_type_by_key_name(db, key_name=key_name_to_search, user_id=current_user.id)
        
        if not db_product_type:
            print(f"ROUTER: Não encontrado como tipo do usuário. Tentando buscar globalmente por key_name: '{key_name_to_search}' (user_id: None)") 
            db_product_type = crud.get_product_type_by_key_name(db, key_name=key_name_to_search, user_id=None)

    if db_product_type is None:
        print(f"ROUTER: Tipo de produto NÃO encontrado para identificador '{identifier}' após todas as tentativas.") 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tipo de Produto com identificador '{identifier}' não encontrado.")
    
    is_global = db_product_type.user_id is None
    is_owner = db_product_type.user_id == current_user.id

    if not (current_user.is_superuser or is_global or is_owner):
        print(f"ROUTER: Permissão NEGADA para usuário ID {current_user.id} acessar tipo de produto ID {db_product_type.id} (Owner: {db_product_type.user_id}, Global: {is_global})")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a visualizar este tipo de produto.")
    
    print(f"ROUTER: Permissão CONCEDIDA. Retornando tipo de produto ID {db_product_type.id} ('{db_product_type.friendly_name}')") 
    return db_product_type
# --- FIM DA ROTA MODIFICADA ---


@router.put("/{type_id}", response_model=schemas.ProductTypeResponse)
def update_product_type_endpoint( 
    type_id: int, 
    product_type_in: schemas.ProductTypeUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    print(f"ROUTER (update_product_type): Tentando atualizar tipo de produto ID {type_id} para usuário ID {current_user.id}")
    updated_type = crud.update_product_type(db=db, product_type_id=type_id, product_type_data=product_type_in, user_id=current_user.id)
    if not updated_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de produto não encontrado ou falha na atualização.")
    print(f"ROUTER (update_product_type): Tipo de produto ID {type_id} atualizado com sucesso.")
    return updated_type

@router.delete("/{type_id}", response_model=schemas.ProductTypeResponse) 
def delete_product_type_endpoint( 
    type_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    print(f"ROUTER (delete_product_type): Tentando deletar tipo de produto ID {type_id} para usuário ID {current_user.id}")
    deleted_type = crud.delete_product_type(db=db, product_type_id=type_id, user_id=current_user.id)
    if not deleted_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado para deleção ou não pôde ser deletado.")
    print(f"ROUTER (delete_product_type): Tipo de produto ID {type_id} deletado com sucesso.")
    return deleted_type

@router.post("/{type_id}/attributes/", response_model=schemas.AttributeTemplateResponse, status_code=status.HTTP_201_CREATED)
def add_attribute_to_product_type_endpoint( 
    type_id: int,
    attribute_in: schemas.AttributeTemplateCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    print(f"ROUTER (add_attribute): Tentando adicionar atributo ao tipo ID {type_id} para usuário ID {current_user.id}")
    existing_attr_template = db.query(models.AttributeTemplate).filter(
        models.AttributeTemplate.product_type_id == type_id,
        models.AttributeTemplate.attribute_key == attribute_in.attribute_key
    ).first()
    if existing_attr_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Um atributo com a chave '{attribute_in.attribute_key}' já existe para este tipo de produto."
        )
    
    new_attribute = crud.create_attribute_template(db=db, attribute_template_data=attribute_in, product_type_id=type_id, user_id=current_user.id)
    print(f"ROUTER (add_attribute): Atributo '{new_attribute.label}' adicionado ao tipo ID {type_id}.")
    return new_attribute

@router.put("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def update_attribute_for_product_type_endpoint( 
    type_id: int, 
    attribute_id: int,
    attribute_in: schemas.AttributeTemplateUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    print(f"ROUTER (update_attribute): Tentando atualizar atributo ID {attribute_id} do tipo ID {type_id} para usuário ID {current_user.id}")
    db_attribute_to_check = crud.get_attribute_template(db, attribute_id)
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

    updated_attribute = crud.update_attribute_template(db=db, attribute_template_id=attribute_id, attribute_template_data=attribute_in, user_id=current_user.id)
    if not updated_attribute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao atualizar o atributo.")
    print(f"ROUTER (update_attribute): Atributo ID {attribute_id} atualizado.")
    return updated_attribute

@router.delete("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def remove_attribute_from_product_type_endpoint( 
    type_id: int, 
    attribute_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    print(f"ROUTER (delete_attribute): Tentando deletar atributo ID {attribute_id} do tipo ID {type_id} para usuário ID {current_user.id}")
    db_attribute_to_check = crud.get_attribute_template(db, attribute_id)
    if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo não encontrado ou não pertence ao tipo de produto especificado para deleção.")

    deleted_attribute = crud.delete_attribute_template(db=db, attribute_template_id=attribute_id, user_id=current_user.id)
    if not deleted_attribute: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao deletar o atributo.")
    print(f"ROUTER (delete_attribute): Atributo ID {attribute_id} deletado.")
    return deleted_attribute