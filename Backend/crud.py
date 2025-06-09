# Backend/crud.py
import logging
import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, and_, desc, asc, extract # Adicionado extract
from sqlalchemy.orm import Session, joinedload, selectinload, aliased
from sqlalchemy.exc import IntegrityError

from jose import jwt # Para decodificar token se necessário (ex: social_auth)

from Backend.core.config import settings  # Para JWT_SECRET_KEY, ALGORITHM, etc.
from Backend.core import security  # Para hash de senha
from pathlib import Path
import uuid
from fastapi import UploadFile
from Backend.models import (  # Isso está correto
    User, Role, Plano, Produto, Fornecedor, ProductType, AttributeTemplate, RegistroUsoIA,
    StatusEnriquecimentoEnum, StatusGeracaoIAEnum, TipoAcaoIAEnum, AttributeFieldTypeEnum
)
from Backend import schemas # Importa todos os schemas

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from .crud_users import *
from .crud_fornecedores import *
from .crud_produtos import *

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

# --- RegistroUsoIA CRUD ---
def create_registro_uso_ia(db: Session, registro_uso: schemas.RegistroUsoIACreate) -> RegistroUsoIA:
    # user_id é obrigatório em RegistroUsoIACreate, então não precisa ser passado separadamente
    db_registro = RegistroUsoIA(**registro_uso.model_dump())
    db.add(db_registro)
    db.commit()
    db.refresh(db_registro)
    return db_registro

def get_registros_uso_ia(
    db: Session,
    user_id: Optional[int] = None,
    produto_id: Optional[int] = None,
    tipo_acao: Optional[TipoAcaoIAEnum] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[RegistroUsoIA]:
    query = db.query(RegistroUsoIA)
    if user_id:
        query = query.filter(RegistroUsoIA.user_id == user_id)
    if produto_id:
        query = query.filter(RegistroUsoIA.produto_id == produto_id)
    if tipo_acao:
        query = query.filter(RegistroUsoIA.tipo_acao == tipo_acao)
    if data_inicio:
        query = query.filter(RegistroUsoIA.created_at >= data_inicio) # CORRIGIDO de .timestamp
    if data_fim:
        query = query.filter(RegistroUsoIA.created_at <= data_fim) # CORRIGIDO de .timestamp
    
    return query.order_by(RegistroUsoIA.created_at.desc()).offset(skip).limit(limit).all() # CORRIGIDO de .timestamp

def count_registros_uso_ia(
    db: Session,
    user_id: Optional[int] = None,
    produto_id: Optional[int] = None,
    tipo_acao: Optional[TipoAcaoIAEnum] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None
) -> int:
    query = db.query(func.count(RegistroUsoIA.id))
    if user_id:
        query = query.filter(RegistroUsoIA.user_id == user_id)
    if produto_id:
        query = query.filter(RegistroUsoIA.produto_id == produto_id)
    if tipo_acao:
        query = query.filter(RegistroUsoIA.tipo_acao == tipo_acao)
    if data_inicio:
        query = query.filter(RegistroUsoIA.created_at >= data_inicio) # CORRIGIDO de .timestamp
    if data_fim:
        query = query.filter(RegistroUsoIA.created_at <= data_fim) # CORRIGIDO de .timestamp

    count = query.scalar()
    return count if count is not None else 0


# --- Admin Analytics CRUD functions ---
def get_total_usuarios_count(db: Session) -> int:
    return db.query(func.count(User.id)).scalar() or 0

def get_total_produtos_count(db: Session, user_id: Optional[int] = None) -> int:
    query = db.query(func.count(Produto.id))
    if user_id: # Se um user_id específico for fornecido (ex: admin vendo produtos de um usuário)
        query = query.filter(Produto.user_id == user_id)
    return query.scalar() or 0

def get_total_fornecedores_count(db: Session, user_id: Optional[int] = None) -> int:
    query = db.query(func.count(Fornecedor.id))
    if user_id:
        query = query.filter(Fornecedor.user_id == user_id)
    return query.scalar() or 0

def get_geracoes_ia_count_no_mes_corrente(db: Session, user_id: Optional[int] = None) -> int:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(func.count(RegistroUsoIA.id)).filter(
        RegistroUsoIA.created_at >= start_of_month,  # CORRIGIDO de .timestamp
        RegistroUsoIA.tipo_acao.notin_([TipoAcaoIAEnum.ENRIQUECIMENTO_WEB_PRODUTO]) # Exclui enriquecimento
    )
    if user_id:
        query = query.filter(RegistroUsoIA.user_id == user_id)
    return query.scalar() or 0

def get_enriquecimentos_count_no_mes_corrente(db: Session, user_id: Optional[int] = None) -> int:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(func.count(RegistroUsoIA.id)).filter(
        RegistroUsoIA.created_at >= start_of_month,  # CORRIGIDO de .timestamp
        RegistroUsoIA.tipo_acao == TipoAcaoIAEnum.ENRIQUECIMENTO_WEB_PRODUTO
    )
    if user_id:
        query = query.filter(RegistroUsoIA.user_id == user_id)
    return query.scalar() or 0

def count_usos_ia_by_user_and_type_no_mes_corrente(db: Session, user_id: int, tipo_geracao_prefix: str) -> int:
    """Retorna a quantidade de usos de IA de um tipo dado para o usuário no mês corrente."""
    start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    query = (
        db.query(func.count(RegistroUsoIA.id))
        .filter(
            RegistroUsoIA.user_id == user_id,
            RegistroUsoIA.created_at >= start_of_month,
            RegistroUsoIA.tipo_acao.ilike(f"{tipo_geracao_prefix}%")
        )
    )
    return query.scalar() or 0

def get_uso_ia_por_plano_no_mes(db: Session) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Alias para User e Plano para facilitar o join e a seleção de nomes
    Usuario = aliased(User)
    PlanoInfo = aliased(Plano)

    results = db.query(
        PlanoInfo.id.label("plano_id"),
        PlanoInfo.nome.label("nome_plano"),
        func.count(RegistroUsoIA.id).label("total_geracoes_ia_no_mes")
    ).join(Usuario, RegistroUsoIA.user_id == Usuario.id)\
     .outerjoin(PlanoInfo, Usuario.plano_id == PlanoInfo.id)\
     .filter(RegistroUsoIA.created_at >= start_of_month)\
     .group_by(PlanoInfo.id, PlanoInfo.nome)\
     .order_by(desc("total_geracoes_ia_no_mes"))\
     .all()
    
    # Lidar com usuários sem plano (plano_id é None)
    count_sem_plano = db.query(
        func.count(RegistroUsoIA.id)
    ).join(Usuario, RegistroUsoIA.user_id == Usuario.id)\
    .filter(
        RegistroUsoIA.created_at >= start_of_month,
        Usuario.plano_id == None
    ).scalar() or 0

    # Adicionar como um item separado ou como preferir
    output = []
    for row in results:
        output.append({
            "plano_id": row.plano_id,
            "nome_plano": row.nome_plano if row.plano_id else "Sem Plano", # Nomeia corretamente
            "total_geracoes_ia_no_mes": row.total_geracoes_ia_no_mes
        })
    
    if count_sem_plano > 0:
        sem_plano_presente = any(item["plano_id"] is None for item in output)
        if not sem_plano_presente:
            output.append({
                "plano_id": None,
                "nome_plano": "Sem Plano",
                "total_geracoes_ia_no_mes": count_sem_plano
            })
        else: # Atualizar a contagem se já existir
            for item in output:
                if item["plano_id"] is None:
                    item["total_geracoes_ia_no_mes"] = count_sem_plano
                    break
    return output


def get_uso_ia_por_usuario_no_mes(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    Usuario = aliased(User)
    PlanoInfo = aliased(Plano)

    results = db.query(
        Usuario.id.label("user_id"),
        Usuario.email.label("email_usuario"),
        PlanoInfo.nome.label("nome_plano"),
        func.count(RegistroUsoIA.id).label("total_geracoes_ia_no_mes")
    ).join(Usuario, RegistroUsoIA.user_id == Usuario.id)\
     .outerjoin(PlanoInfo, Usuario.plano_id == PlanoInfo.id)\
     .filter(RegistroUsoIA.created_at >= start_of_month)\
     .group_by(Usuario.id, Usuario.email, PlanoInfo.nome)\
     .order_by(desc("total_geracoes_ia_no_mes"))\
     .limit(limit)\
     .all()
    
    return [
        {
            "user_id": row.user_id,
            "email_usuario": row.email_usuario,
            "nome_plano": row.nome_plano if row.nome_plano else "Sem Plano",
            "total_geracoes_ia_no_mes": row.total_geracoes_ia_no_mes
        } for row in results
    ]

def get_uso_ia_por_tipo_no_mes(db: Session) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    results = db.query(
        RegistroUsoIA.tipo_acao,
        func.count(RegistroUsoIA.id).label("total_no_mes")
    ).filter(RegistroUsoIA.created_at >= start_of_month)\
     .group_by(RegistroUsoIA.tipo_acao)\
     .order_by(desc("total_no_mes"))\
     .all()
    
    return [
        {"tipo_acao": row.tipo_acao.value, "total_no_mes": row.total_no_mes} for row in results
    ]


def get_active_users_with_activity(db: Session, limit: int = 20) -> List[User]:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Subquery para contagem de produtos por usuário
    subquery_produtos = db.query(
        Produto.user_id,
        func.count(Produto.id).label("total_produtos")
    ).group_by(Produto.user_id).subquery()

    # Subquery para contagem de gerações IA no mês por usuário
    subquery_ia = db.query(
        RegistroUsoIA.user_id,
        func.count(RegistroUsoIA.id).label("total_geracoes_ia_mes_corrente")
    ).filter(RegistroUsoIA.created_at >= start_of_month)\
     .group_by(RegistroUsoIA.user_id).subquery()

    users = db.query(
        User,
        subquery_produtos.c.total_produtos,
        subquery_ia.c.total_geracoes_ia_mes_corrente
    ).outerjoin(subquery_produtos, User.id == subquery_produtos.c.user_id)\
     .outerjoin(subquery_ia, User.id == subquery_ia.c.user_id)\
     .filter(User.is_active == True)\
     .order_by(User.created_at.desc())\
     .limit(limit)\
     .all()
    
    # Adicionar atributos dinamicamente para o schema UserActivity funcionar
    user_activity_list = []
    for user_model, total_prods, total_ia in users:
        setattr(user_model, 'total_produtos', total_prods or 0)
        setattr(user_model, 'total_geracoes_ia_mes_corrente', total_ia or 0)
        user_activity_list.append(user_model)

    return user_activity_list


# Função auxiliar para o startup (main.py)
def create_initial_data(db: Session):
    logger.info("Verificando/criando dados iniciais (roles, planos, admin)...")
    
    # Criar Roles Padrão
    roles_padrao = [
        {"name": "admin", "description": "Administrador do sistema"},
        {"name": "user", "description": "Usuário padrão da plataforma"},
    ]
    for role_data in roles_padrao:
        role = get_role_by_name(db, role_data["name"])
        if not role:
            create_role(db, schemas.RoleCreate(**role_data))
            logger.info(f"Role '{role_data['name']}' criada.")

    # Criar Planos Padrão
    planos_padrao = [
        {
            "nome": "Gratuito", "descricao": "Plano básico com limitações.",
            "preco_mensal": 0.0, "limite_produtos": settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO,
            "limite_enriquecimento_web": settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO,
            "limite_geracao_ia": settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO,
            "permite_api_externa": False, "suporte_prioritario": False
        },
        {
            "nome": "Pro", "descricao": "Plano profissional com mais limites e funcionalidades.",
            "preco_mensal": 99.90, "limite_produtos": 1000,
            "limite_enriquecimento_web": 500, "limite_geracao_ia": 2000,
            "permite_api_externa": True, "suporte_prioritario": True
        },
    ]
    for plano_data in planos_padrao:
        plano = get_plano_by_name(db, plano_data["nome"])
        if not plano:
            create_plano(db, schemas.PlanoCreate(**plano_data))
            logger.info(f"Plano '{plano_data['nome']}' criado.")

    # Criar Usuário Administrador Padrão
    admin_email = settings.FIRST_SUPERUSER_EMAIL
    admin_password = settings.FIRST_SUPERUSER_PASSWORD
    admin_user = get_user_by_email(db, admin_email)
    if not admin_user:
        admin_role = get_role_by_name(db, "admin")
        admin_plano = get_plano_by_name(db, "Pro")

        user_in = schemas.UserCreate(
            email=admin_email,
            password=admin_password,
            nome_completo="Admin TDAI",
            plano_id=admin_plano.id if admin_plano else None
        )
        db_admin_user = create_user(db, user_in)
        db_admin_user.is_superuser = True
        if admin_role:
            db_admin_user.role_id = admin_role.id
        
        db.commit()
        db.refresh(db_admin_user)
        admin_user = db_admin_user
        logger.info(f"Usuário administrador '{admin_email}' criado com sucesso.")
    else:
        logger.info(f"Usuário administrador '{admin_email}' já existe.")


    # Criar Tipos de Produto Globais Padrão (user_id = None)
    tipos_produto_globais = [
        {
            "key_name": "eletronicos", 
            "friendly_name": "Eletrônicos",
            "description": "Tipo padrão para produtos eletrônicos.",
            "attribute_templates": [
                schemas.AttributeTemplateCreate(attribute_key="voltagem", label="Voltagem", field_type=AttributeFieldTypeEnum.SELECT, options='["110V", "220V", "Bivolt"]', is_required=True, display_order=1),
                schemas.AttributeTemplateCreate(attribute_key="cor_predominante", label="Cor Predominante", field_type=AttributeFieldTypeEnum.TEXT, is_required=False, display_order=2),
                schemas.AttributeTemplateCreate(attribute_key="garantia_meses", label="Garantia (meses)", field_type=AttributeFieldTypeEnum.NUMBER, default_value="12", display_order=3),
            ]
        },
        {
            "key_name": "vestuario",
            "friendly_name": "Vestuário",
            "description": "Tipo padrão para peças de vestuário.",
            "attribute_templates": [
                schemas.AttributeTemplateCreate(
                    attribute_key="tamanho",
                    label="Tamanho",
                    field_type=AttributeFieldTypeEnum.SELECT,
                    options='["P", "M", "G", "GG"]',
                    is_required=True,
                    display_order=1
                ),
                schemas.AttributeTemplateCreate(
                    attribute_key="cor_produto",
                    label="Cor",
                    field_type=AttributeFieldTypeEnum.TEXT,
                    is_required=True,
                    display_order=2
                ),
                schemas.AttributeTemplateCreate(
                    attribute_key="material_principal",
                    label="Material Principal",
                    field_type=AttributeFieldTypeEnum.TEXT,
                    display_order=3
                ),
                schemas.AttributeTemplateCreate(
                    attribute_key="genero_vestuario",
                    label="Gênero",
                    field_type=AttributeFieldTypeEnum.SELECT,
                    options='["Masculino", "Feminino", "Unissex"]',
                    display_order=4
                ),
            ]
        }
    ]

    for pt_data in tipos_produto_globais:
        pt_create_schema = schemas.ProductTypeCreate(**pt_data)

        existing_pt = get_product_type_by_key_name(db, key_name=pt_create_schema.key_name, user_id=None) # user_id=None para globais
        if not existing_pt:
            try:
                create_product_type(db, product_type_create=pt_create_schema, user_id=None) # user_id=None para globais
                logger.info(f"Tipo de Produto Global '{pt_create_schema.friendly_name}' criado.")
            except IntegrityError as e:
                logger.warning(f"Não foi possível criar o tipo de produto global '{pt_create_schema.key_name}': {e}")
            except Exception as e:
                logger.error(f"Erro inesperado ao criar tipo de produto global '{pt_create_schema.key_name}': {e}", exc_info=True)
        else:
            logger.info(f"Tipo de Produto Global '{pt_create_schema.friendly_name}' já existe.")

    # Criar Fornecedor Padrão do Administrador
    if admin_user:
        fornecedor_existente = db.query(Fornecedor).filter(
            func.lower(Fornecedor.nome) == "uouu",
            Fornecedor.user_id == admin_user.id,
        ).first()
        if not fornecedor_existente:
            fornecedor_schema = schemas.FornecedorCreate(
                nome="UouU",
                site_url="www.uouu.com.br",
            )
            create_fornecedor(db, fornecedor_schema, user_id=admin_user.id)
            logger.info("Fornecedor de exemplo 'UouU' criado para o administrador.")
        else:
            logger.info("Fornecedor de exemplo 'UouU' já existe para o administrador.")

    logger.info("Criação/verificação de dados iniciais concluída.")

