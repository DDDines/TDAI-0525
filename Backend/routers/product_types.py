# Backend/routers/product_types.py

from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Path as FastAPIPath # Renomeado Path para FastAPIPath
from sqlalchemy.orm import Session

import crud
import models
import schemas
import database # Para get_db
from . import auth_utils # Para get_current_active_user

# Não precisa de app aqui, ele é definido e usado em main.py
# from main import app # REMOVER ESTA LINHA SE EXISTIR

router = APIRouter(
    prefix="/product-types", # O prefixo /api/v1 será adicionado em main.py
    tags=["Tipos de Produto e Templates de Atributos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

# Endpoints para ProductType
@router.post("/", response_model=schemas.ProductTypeResponse, status_code=status.HTTP_201_CREATED)
def create_product_type(
    product_type_in: schemas.ProductTypeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # Verificar se já existe um tipo de produto com a mesma key_name (global ou do usuário)
    # Esta lógica pode ser mais complexa dependendo se key_name deve ser única globalmente ou por usuário.
    # Assumindo que key_name é globalmente única por enquanto, como no modelo.
    existing_type = crud.get_product_type_by_key_name(db, key_name=product_type_in.key_name)
    if existing_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Um tipo de produto com a chave '{product_type_in.key_name}' já existe."
        )
    # user_id=None para tipos globais, ou current_user.id se for específico do usuário
    # A lógica atual do modelo ProductType permite user_id opcional.
    # Se a regra for que tipos criados por usuários não-admin são deles, e admin cria globais:
    user_id_for_type = current_user.id if not current_user.is_superuser else None # Exemplo de lógica
    # Ou sempre None se todos os tipos são globais, ou sempre current_user.id se são sempre do usuário.
    # A chamada crud.create_product_type já aceita user_id opcional.
    return crud.create_product_type(db=db, product_type_data=product_type_in, user_id=user_id_for_type)


@router.get("/", response_model=List[schemas.ProductTypeResponse])
def read_product_types(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # Se usuários normais só podem ver os seus tipos + tipos globais (user_id=None)
    # E admins veem todos.
    # A função crud.get_product_types já tem um parâmetro user_id para essa lógica.
    user_id_filter = current_user.id if not current_user.is_superuser else None
    # Se user_id_filter for None, o CRUD deve retornar todos (ou apenas os globais, dependendo da implementação)
    # Se user_id_filter tiver um ID, o CRUD deve retornar os desse usuário + os globais.
    product_types = crud.get_product_types(db, skip=skip, limit=limit, user_id=user_id_filter)
    return product_types

@router.get("/{type_id_or_key}", response_model=schemas.ProductTypeResponse)
def read_product_type_details(
    type_id_or_key: Union[int, str], # Aceita ID (int) ou key_name (str)
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_product_type = None
    if isinstance(type_id_or_key, int):
        db_product_type = crud.get_product_type(db, product_type_id=type_id_or_key)
    else: # é string (key_name)
        db_product_type = crud.get_product_type_by_key_name(db, key_name=type_id_or_key)
    
    if db_product_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado.")
    
    # Lógica de permissão: usuário só pode ver os seus ou os globais, a menos que seja admin
    if not current_user.is_superuser and db_product_type.user_id is not None and db_product_type.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a visualizar este tipo de produto.")
        
    return db_product_type

@router.put("/{type_id}", response_model=schemas.ProductTypeResponse)
def update_product_type(
    type_id: int, 
    product_type_in: schemas.ProductTypeUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_product_type = crud.get_product_type(db, product_type_id=type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado.")
    
    # Lógica de permissão para atualização
    if not current_user.is_superuser and db_product_type.user_id != current_user.id:
        # Se user_id for None (global), um não-admin também não deveria poder alterar,
        # a menos que haja uma regra específica. Assumindo que só owner ou admin podem.
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a modificar este tipo de produto.")

    # Verificar se a nova key_name (se alterada) já existe
    if product_type_in.key_name and product_type_in.key_name != db_product_type.key_name:
        existing_type = crud.get_product_type_by_key_name(db, key_name=product_type_in.key_name)
        if existing_type and existing_type.id != type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Um tipo de produto com a chave '{product_type_in.key_name}' já existe."
            )
    return crud.update_product_type(db=db, product_type_id=type_id, product_type_data=product_type_in)

@router.delete("/{type_id}", response_model=schemas.ProductTypeResponse) # Ou apenas um Msg de sucesso
def delete_product_type(
    type_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_product_type = crud.get_product_type(db, product_type_id=type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado.")

    # Lógica de permissão para deleção
    if not current_user.is_superuser and db_product_type.user_id != current_user.id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a deletar este tipo de produto.")
    
    # Adicionar verificação se o tipo de produto está em uso por algum produto antes de deletar
    # produtos_usando_tipo = db.query(models.Produto).filter(models.Produto.product_type_id == type_id).first()
    # if produtos_usando_tipo:
    #     raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este tipo de produto está em uso e não pode ser deletado.")

    deleted_type = crud.delete_product_type(db=db, product_type_id=type_id)
    if not deleted_type: # Deveria ter sido pego pelo get_product_type, mas por segurança
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado para deleção.")
    return deleted_type


# Endpoints para AttributeTemplate aninhados em ProductType
@router.post("/{type_id}/attributes/", response_model=schemas.AttributeTemplateResponse, status_code=status.HTTP_201_CREATED)
def add_attribute_to_product_type(
    type_id: int,
    attribute_in: schemas.AttributeTemplateCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_product_type = crud.get_product_type(db, product_type_id=type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado para adicionar atributo.")
    
    if not current_user.is_superuser and db_product_type.user_id != current_user.id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a modificar atributos deste tipo de produto.")

    # Verificar se attribute_key já existe para este product_type_id
    existing_attr = db.query(models.AttributeTemplate).filter(
        models.AttributeTemplate.product_type_id == type_id,
        models.AttributeTemplate.attribute_key == attribute_in.attribute_key
    ).first()
    if existing_attr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Atributo com a chave '{attribute_in.attribute_key}' já existe para este tipo de produto."
        )
    return crud.create_attribute_template(db=db, attribute_template_data=attribute_in, product_type_id=type_id)


@router.put("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def update_attribute_for_product_type(
    type_id: int,
    attribute_id: int,
    attribute_in: schemas.AttributeTemplateUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_product_type = crud.get_product_type(db, product_type_id=type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado.")

    if not current_user.is_superuser and db_product_type.user_id != current_user.id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a modificar atributos deste tipo de produto.")

    db_attribute = crud.get_attribute_template(db, attribute_template_id=attribute_id)
    if not db_attribute or db_attribute.product_type_id != type_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo não encontrado ou não pertence a este tipo de produto.")

    # Se attribute_key for alterada, verificar duplicação
    if attribute_in.attribute_key and attribute_in.attribute_key != db_attribute.attribute_key:
        existing_attr = db.query(models.AttributeTemplate).filter(
            models.AttributeTemplate.product_type_id == type_id,
            models.AttributeTemplate.attribute_key == attribute_in.attribute_key,
            models.AttributeTemplate.id != attribute_id # Exclui o próprio atributo da checagem
        ).first()
        if existing_attr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Atributo com a chave '{attribute_in.attribute_key}' já existe para este tipo de produto."
            )
    return crud.update_attribute_template(db=db, attribute_template_id=attribute_id, attribute_template_data=attribute_in)


@router.delete("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse) # Ou Msg
def remove_attribute_from_product_type(
    type_id: int,
    attribute_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_product_type = crud.get_product_type(db, product_type_id=type_id)
    if not db_product_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de Produto não encontrado.")

    if not current_user.is_superuser and db_product_type.user_id != current_user.id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a modificar atributos deste tipo de produto.")

    db_attribute = crud.get_attribute_template(db, attribute_template_id=attribute_id)
    if not db_attribute or db_attribute.product_type_id != type_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atributo não encontrado ou não pertence a este tipo de produto.")
    
    deleted_attribute = crud.delete_attribute_template(db=db, attribute_template_id=attribute_id)
    if not deleted_attribute: # Segurança
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao deletar o atributo.")
    return deleted_attribute

# A linha problemática "app.include_router(product_types.router)" foi REMOVIDA daqui.