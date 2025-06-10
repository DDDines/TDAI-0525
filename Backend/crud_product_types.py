import logging
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from Backend.models import Produto, ProductType, AttributeTemplate
from Backend import schemas

logger = logging.getLogger(__name__)

# --- ProductType CRUD ---
def create_product_type(db: Session, product_type_create: schemas.ProductTypeCreate, user_id: Optional[int] = None) -> ProductType:
    logger.debug(f"CRUD (create_product_type): Recebido para user_id: {user_id}, key_name: {product_type_create.key_name}")
    
    # Verifica se já existe um tipo de produto com o mesmo key_name (global ou do usuário)
    existing_pt_query = db.query(ProductType).filter(ProductType.key_name == product_type_create.key_name)
    if user_id:
        existing_pt_query = existing_pt_query.filter(or_(ProductType.user_id == user_id, ProductType.user_id == None))
    else: # Global
        existing_pt_query = existing_pt_query.filter(ProductType.user_id == None)
    
    existing_pt = existing_pt_query.first()
    if existing_pt:
        # Se for um tipo global e o usuário está tentando criar um com a mesma chave
        if existing_pt.user_id is None and user_id is not None:
            raise IntegrityError(f"Um Tipo de Produto global com a chave '{product_type_create.key_name}' já existe.", params={}, orig=None)
        # Se for um tipo do usuário e ele está tentando criar um com a mesma chave
        elif existing_pt.user_id == user_id:
            raise IntegrityError(f"Você já possui um Tipo de Produto com a chave '{product_type_create.key_name}'.", params={}, orig=None)
        # Se for uma tentativa de criar um global que já existe
        elif user_id is None and existing_pt.user_id is None:
            raise IntegrityError(f"Um Tipo de Produto global com a chave '{product_type_create.key_name}' já existe.", params={}, orig=None)


    db_product_type = ProductType(
        key_name=product_type_create.key_name,
        friendly_name=product_type_create.friendly_name,
        description=product_type_create.description if hasattr(product_type_create, 'description') else None,
        user_id=user_id
    )
    db.add(db_product_type)
    db.flush() # Para obter o ID do product_type antes de adicionar atributos

    if hasattr(product_type_create, 'attribute_templates') and product_type_create.attribute_templates:
        for attr_template_data in product_type_create.attribute_templates:
            db_attr_template = AttributeTemplate(
                **attr_template_data.model_dump(),
                product_type_id=db_product_type.id
            )
            db.add(db_attr_template)
    
    db.commit()
    db.refresh(db_product_type)
    # Para carregar os attribute_templates recém-criados na resposta
    db.refresh(db_product_type, attribute_names=['attribute_templates']) 
    logger.info(f"CRUD (create_product_type): Tipo de Produto '{db_product_type.friendly_name}' (ID: {db_product_type.id}) criado para user_id: {user_id}")
    return db_product_type

def get_product_type(db: Session, product_type_id: int) -> Optional[ProductType]:
    return db.query(ProductType).options(selectinload(ProductType.attribute_templates)).filter(ProductType.id == product_type_id).first()

def get_product_type_by_key_name(db: Session, key_name: str, user_id: Optional[int] = None) -> Optional[ProductType]:
    logger.debug(f"CRUD (get_product_type_by_key_name): Buscando tipo de produto por KeyName: '{key_name}', UserID: {user_id}")
    query = db.query(ProductType).options(selectinload(ProductType.attribute_templates)).filter(ProductType.key_name == key_name)
    if user_id:
        # Usuário pode acessar seus próprios tipos ou tipos globais
        pt = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id == None)).order_by(ProductType.user_id.desc()).first() # Prioriza o do usuário
        if pt:
            logger.debug(f"CRUD: Encontrado tipo de produto (user ou global): '{pt.friendly_name}' (ID: {pt.id})")
            return pt
        logger.debug(f"CRUD: Nenhum tipo (user ou global) encontrado para key_name '{key_name}' e user_id '{user_id}'.")
        return None
    else:
        # Busca apenas tipos globais
        pt = query.filter(ProductType.user_id == None).first()
        if pt:
            logger.debug(f"CRUD: Encontrado tipo de produto global: '{pt.friendly_name}' (ID: {pt.id})")
            return pt
        logger.debug(f"CRUD: Nenhum tipo global encontrado para key_name '{key_name}' (user_id não fornecido).")
        return None


def get_product_types_for_user(db: Session, user_id: Optional[int], skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[ProductType]:
    if skip < 0:
        raise ValueError("skip must be non-negative")
    if limit <= 0:
        raise ValueError("limit must be positive")
    query = db.query(ProductType).options(selectinload(ProductType.attribute_templates))
    
    # Filtra para tipos do usuário específico OU tipos globais (user_id IS NULL)
    if user_id:
        query = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id == None))
    else: # Se user_id não for fornecido (ex: admin buscando todos os globais, ou lógica específica)
        # Por agora, vamos assumir que se user_id é None, busca apenas globais.
        # Se a intenção for "todos os tipos de todos os usuários" para um superadmin, a lógica mudaria.
        query = query.filter(ProductType.user_id == None) # Apenas globais

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(ProductType.key_name).ilike(search_term),
                func.lower(ProductType.friendly_name).ilike(search_term),
                func.lower(ProductType.description).ilike(search_term)
            )
        )
        
    return query.order_by(ProductType.user_id.nullslast(), ProductType.friendly_name).offset(skip).limit(limit).all() # Globais primeiro, depois por nome

def count_product_types_for_user(db: Session, user_id: Optional[int], search: Optional[str] = None) -> int:
    query = db.query(func.count(ProductType.id))
    if user_id:
        query = query.filter(or_(ProductType.user_id == user_id, ProductType.user_id == None))
    else:
        query = query.filter(ProductType.user_id == None)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(ProductType.key_name).ilike(search_term),
                func.lower(ProductType.friendly_name).ilike(search_term),
                func.lower(ProductType.description).ilike(search_term)
            )
        )
    count = query.scalar()
    return count if count is not None else 0


def update_product_type(db: Session, db_product_type: ProductType, product_type_update: schemas.ProductTypeUpdate) -> ProductType:
    update_data = product_type_update.model_dump(exclude_unset=True)
    
    if "key_name" in update_data and update_data["key_name"] != db_product_type.key_name:
        # Verificar se a nova key_name já existe para este usuário ou globalmente
        existing_check = db.query(ProductType).filter(
            ProductType.key_name == update_data["key_name"],
            ProductType.id != db_product_type.id # Exclui o próprio registro
        )
        if db_product_type.user_id: # Se for um tipo de usuário
            existing_check = existing_check.filter(or_(ProductType.user_id == db_product_type.user_id, ProductType.user_id == None))
        else: # Se for um tipo global
            existing_check = existing_check.filter(ProductType.user_id == None)
        
        if existing_check.first():
            raise IntegrityError(f"A chave '{update_data['key_name']}' já está em uso.", params={}, orig=None)

    for key, value in update_data.items():
        setattr(db_product_type, key, value)
    
    db.commit()
    db.refresh(db_product_type)
    db.refresh(db_product_type, attribute_names=['attribute_templates']) # Recarregar atributos
    return db_product_type

def delete_product_type(db: Session, db_product_type: ProductType) -> ProductType:
    # Antes de deletar, verificar se há produtos usando este tipo
    # Se houver, impedir a exclusão ou definir product_type_id como NULL nos produtos
    # Por ora, vamos impedir se houver produtos associados
    num_associated_products = db.query(Produto).filter(Produto.product_type_id == db_product_type.id).count()
    if num_associated_products > 0:
        raise IntegrityError(
            f"Não é possível excluir o Tipo de Produto '{db_product_type.friendly_name}' pois ele está associado a {num_associated_products} produto(s).",
            params={}, orig=None
        )

    # AttributeTemplates são deletados por cascade="all, delete-orphan" no modelo ProductType
    db.delete(db_product_type)
    db.commit()
    return db_product_type


# --- AttributeTemplate CRUD ---
# --- AttributeTemplate CRUD ---
def create_attribute_template(db: Session, attr_template_create: schemas.AttributeTemplateCreate, product_type_id: int) -> AttributeTemplate:
    # Verificar se já existe um atributo com a mesma key para o mesmo product_type_id
    existing_attr = db.query(AttributeTemplate).filter(
        AttributeTemplate.product_type_id == product_type_id,
        AttributeTemplate.attribute_key == attr_template_create.attribute_key
    ).first()
    if existing_attr:
        raise IntegrityError(f"O Tipo de Produto ID {product_type_id} já possui um atributo com a chave '{attr_template_create.attribute_key}'.", params={}, orig=None)

    db_attr_template = AttributeTemplate(
        **attr_template_create.model_dump(),
        product_type_id=product_type_id
    )
    db.add(db_attr_template)
    db.commit()
    db.refresh(db_attr_template)
    return db_attr_template

def get_attribute_template(db: Session, attribute_template_id: int) -> Optional[AttributeTemplate]:
    return db.query(AttributeTemplate).filter(AttributeTemplate.id == attribute_template_id).first()

def update_attribute_template(db: Session, db_attr_template: AttributeTemplate, attr_template_update: schemas.AttributeTemplateUpdate) -> AttributeTemplate:
    update_data = attr_template_update.model_dump(exclude_unset=True)
    
    if "attribute_key" in update_data and update_data["attribute_key"] != db_attr_template.attribute_key:
        # Verificar se a nova chave já existe para este product_type
        existing_check = db.query(AttributeTemplate).filter(
            AttributeTemplate.product_type_id == db_attr_template.product_type_id,
            AttributeTemplate.attribute_key == update_data["attribute_key"],
            AttributeTemplate.id != db_attr_template.id
        ).first()
        if existing_check:
            raise IntegrityError(f"O Tipo de Produto ID {db_attr_template.product_type_id} já possui um atributo com a chave '{update_data['attribute_key']}'.", params={}, orig=None)

    for key, value in update_data.items():
        setattr(db_attr_template, key, value)
    db.commit()
    db.refresh(db_attr_template)
    return db_attr_template

def delete_attribute_template(db: Session, db_attr_template: AttributeTemplate) -> AttributeTemplate:
    # Aqui, não há produtos diretamente ligados ao AttributeTemplate, mas sim aos ProductTypes.
    # A exclusão é simples.
    db.delete(db_attr_template)
    db.commit()
    return db_attr_template

# --- NOVA FUNÇÃO PARA REORDENAR ATRIBUTOS ---
def reorder_attribute_template(db: Session, attribute_id: int, direction: str) -> Optional[AttributeTemplate]:
    """Muda a ordem de um atributo dentro de seu tipo de produto."""
    attr_to_move = get_attribute_template(db, attribute_id)
    if not attr_to_move:
        return None

    # Busca todos os atributos "irmãos" ordenados pela ordem atual
    siblings = db.query(AttributeTemplate).filter(
        AttributeTemplate.product_type_id == attr_to_move.product_type_id
    ).order_by(AttributeTemplate.display_order.asc(), AttributeTemplate.id.asc()).all()

    # Se a ordem não estiver definida, inicializa com base na ordem atual
    if any(s.display_order is None for s in siblings):
        for i, s in enumerate(siblings):
            s.display_order = i
        db.commit()
        db.refresh(attr_to_move) # Recarrega o atributo principal

    try:
        current_index = siblings.index(attr_to_move)
    except ValueError:
        return None # Não deveria acontecer

    if direction == "up" and current_index > 0:
        # Troca a ordem com o item anterior
        prev_item = siblings[current_index - 1]
        prev_item.display_order, attr_to_move.display_order = attr_to_move.display_order, prev_item.display_order
        db.commit()
    elif direction == "down" and current_index < len(siblings) - 1:
        # Troca a ordem com o item seguinte
        next_item = siblings[current_index + 1]
        next_item.display_order, attr_to_move.display_order = attr_to_move.display_order, next_item.display_order
        db.commit()
    
    # Normaliza a ordem para garantir que seja sequencial (0, 1, 2...)
    siblings_reordered = db.query(AttributeTemplate).filter(
        AttributeTemplate.product_type_id == attr_to_move.product_type_id
    ).order_by(AttributeTemplate.display_order.asc(), AttributeTemplate.id.asc()).all()

    for i, s in enumerate(siblings_reordered):
        s.display_order = i
    
    db.commit()
    db.refresh(attr_to_move)
    return attr_to_move

