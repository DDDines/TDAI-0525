# tdai_project/Backend/crud.py
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, and_
from typing import Optional, List, Dict, Any

import models
import schemas
from auth import get_password_hash # Supondo que get_password_hash esteja em auth.py
from datetime import datetime, timedelta

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).options(
        selectinload(models.User.plano), 
        selectinload(models.User.role)
    ).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).options(
        selectinload(models.User.plano), 
        selectinload(models.User.role)
    ).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).options(
        selectinload(models.User.plano), 
        selectinload(models.User.role)
    ).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        nome=user.nome,
        idioma_preferido=user.idioma_preferido,
        chave_openai_pessoal=user.chave_openai_pessoal
        # plano_id e role_id podem ser definidos depois ou por um admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: models.User, user_update: schemas.UserUpdate) -> models.User:
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_password(db: Session, db_user: models.User, new_password_hash: str) -> models.User:
    db_user.hashed_password = new_password_hash
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_admin(db: Session, db_user: models.User, user_update: schemas.UserUpdateByAdmin) -> models.User:
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    # Recarregar o usuário com relacionamentos para garantir que estejam atualizados na resposta
    return get_user(db, db_user.id)


def delete_user(db: Session, db_user: models.User):
    # Adicionar lógica para lidar com relacionamentos se necessário (ex: anonimizar produtos)
    db.delete(db_user)
    db.commit()
    return {"message": f"User {db_user.email} deleted successfully."}

# --- Role CRUD ---
def get_role(db: Session, role_id: int) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.id == role_id).first()

def get_role_by_name(db: Session, name: str) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.name == name).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[models.Role]:
    return db.query(models.Role).offset(skip).limit(limit).all()

def create_role(db: Session, role: schemas.RoleCreate) -> models.Role:
    db_role = models.Role(name=role.name, description=role.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

# --- Plano CRUD ---
def get_plano(db: Session, plano_id: int) -> Optional[models.Plano]:
    return db.query(models.Plano).filter(models.Plano.id == plano_id).first()

def get_plano_by_name(db: Session, name: str) -> Optional[models.Plano]:
    return db.query(models.Plano).filter(models.Plano.name == name).first()

def get_planos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Plano]:
    return db.query(models.Plano).offset(skip).limit(limit).all()

def create_plano(db: Session, plano: schemas.PlanoCreate) -> models.Plano:
    db_plano = models.Plano(**plano.model_dump())
    db.add(db_plano)
    db.commit()
    db.refresh(db_plano)
    return db_plano

# --- Fornecedor CRUD ---
def create_fornecedor(db: Session, fornecedor: schemas.FornecedorCreate, user_id: int) -> models.Fornecedor:
    db_fornecedor = models.Fornecedor(**fornecedor.model_dump(), user_id=user_id)
    db.add(db_fornecedor)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor

def get_fornecedor(db: Session, fornecedor_id: int, user_id: int) -> Optional[models.Fornecedor]:
    return db.query(models.Fornecedor).filter(models.Fornecedor.id == fornecedor_id, models.Fornecedor.user_id == user_id).first()

def get_fornecedores(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Fornecedor]:
    return db.query(models.Fornecedor).filter(models.Fornecedor.user_id == user_id).offset(skip).limit(limit).all()

def get_all_fornecedores_admin(db: Session, skip: int = 0, limit: int = 100) -> List[models.Fornecedor]:
    return db.query(models.Fornecedor).offset(skip).limit(limit).all()
    
def update_fornecedor(db: Session, db_fornecedor: models.Fornecedor, fornecedor_update: schemas.FornecedorUpdate) -> models.Fornecedor:
    update_data = fornecedor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_fornecedor, key, value)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor

def delete_fornecedor(db: Session, db_fornecedor: models.Fornecedor) -> models.Fornecedor:
    # Antes de deletar, verificar se há produtos associados e decidir a política
    # Por exemplo, desassociar produtos ou impedir a exclusão.
    # Aqui, simplesmente deletamos.
    db.delete(db_fornecedor)
    db.commit()
    return db_fornecedor

# --- Produto CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate, user_id: int) -> models.Produto:
    db_produto = models.Produto(
        **produto.model_dump(exclude_unset=True), # Usar exclude_unset para não sobrescrever defaults do modelo com None
        user_id=user_id
    )
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto
    
def get_produto(db: Session, produto_id: int, user_id: Optional[int] = None) -> Optional[models.Produto]:
    query = db.query(models.Produto).options(selectinload(models.Produto.fornecedor))
    if user_id:
        query = query.filter(models.Produto.id == produto_id, models.Produto.user_id == user_id)
    else: # Admin ou sistema pode buscar sem user_id
        query = query.filter(models.Produto.id == produto_id)
    return query.first()

def get_produtos(
    db: Session, 
    user_id: Optional[int] = None, 
    skip: int = 0, 
    limit: int = 10,
    search_term: Optional[str] = None,
    status_enriquecimento_web: Optional[str] = None,
    status_titulo_ia: Optional[str] = None,
    status_descricao_ia: Optional[str] = None,
    fornecedor_id: Optional[int] = None,
    sort_by: Optional[str] = "created_at", # Default sort
    sort_order: Optional[str] = "desc" # Default order
) -> Dict[str, Any]:
    query = db.query(models.Produto).options(selectinload(models.Produto.fornecedor))

    if user_id:
        query = query.filter(models.Produto.user_id == user_id)

    if search_term:
        search_filter = or_(
            models.Produto.nome_base.ilike(f"%{search_term}%"),
            models.Produto.marca.ilike(f"%{search_term}%"),
            # Ajuste para JSONB - pode precisar de adaptação ao seu dialeto SQL específico se não for PostgreSQL
            # ou se a estrutura de dados_brutos['sku_original'] não for garantida.
            # Considerar um campo SKU dedicado no modelo Produto se for frequentemente pesquisado.
            (models.Produto.dados_brutos['sku_original'].astext.ilike(f"%{search_term}%") if hasattr(models.Produto.dados_brutos, 'astext') else False)
        )
        query = query.filter(search_filter)
    
    if status_enriquecimento_web:
        try:
            status_enum = models.StatusEnriquecimentoEnum[status_enriquecimento_web.upper()]
            query = query.filter(models.Produto.status_enriquecimento_web == status_enum)
        except KeyError:
            pass # Ignorar filtro se o status for inválido
            
    if status_titulo_ia:
        try:
            status_enum = models.StatusGeracaoIAEnum[status_titulo_ia.upper()]
            query = query.filter(models.Produto.status_titulo_ia == status_enum)
        except KeyError:
            pass

    if status_descricao_ia:
        try:
            status_enum = models.StatusGeracaoIAEnum[status_descricao_ia.upper()]
            query = query.filter(models.Produto.status_descricao_ia == status_enum)
        except KeyError:
            pass
            
    if fornecedor_id:
        query = query.filter(models.Produto.fornecedor_id == fornecedor_id)

    # Sorting
    if sort_by and hasattr(models.Produto, sort_by):
        column_to_sort = getattr(models.Produto, sort_by)
        if sort_order.lower() == "asc":
            query = query.order_by(column_to_sort.asc())
        else:
            query = query.order_by(column_to_sort.desc())
    else: # Default sort if invalid sort_by is provided
        query = query.order_by(models.Produto.created_at.desc())


    total_items = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {"items": items, "total_items": total_items, "limit": limit, "skip": skip}

def update_produto(db: Session, db_produto: models.Produto, produto_update: schemas.ProdutoUpdate) -> models.Produto:
    update_data = produto_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_produto, key, value)
    db.commit()
    db.refresh(db_produto)
    # Eager load 'fornecedor' again after refresh if it's needed by the response schema
    db.refresh(db_produto, attribute_names=['fornecedor']) 
    return db_produto

def delete_produto(db: Session, db_produto: models.Produto) -> models.Produto:
    # Adicionar lógica para lidar com relacionamentos (ex: UsoIA) se necessário
    db.delete(db_produto)
    db.commit()
    return db_produto

def get_produtos_by_ids(db: Session, produto_ids: List[int], user_id: int) -> List[models.Produto]:
    return db.query(models.Produto).filter(
        models.Produto.id.in_(produto_ids),
        models.Produto.user_id == user_id
    ).all()

# --- UsoIA CRUD ---
def create_uso_ia(db: Session, uso_ia: schemas.UsoIACreate, user_id: int) -> models.UsoIA:
    db_uso_ia = models.UsoIA(
        **uso_ia.model_dump(),
        user_id=user_id,
        timestamp=datetime.utcnow() # Garante que o timestamp é UTC
    )
    db.add(db_uso_ia)
    db.commit()
    db.refresh(db_uso_ia)
    return db_uso_ia

def get_usos_ia_por_usuario_periodo(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> List[models.UsoIA]:
    return db.query(models.UsoIA).filter(
        models.UsoIA.user_id == user_id,
        models.UsoIA.timestamp >= start_date,
        models.UsoIA.timestamp < end_date
    ).all()

def get_usos_ia_por_produto(db: Session, produto_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[models.UsoIA]:
    return db.query(models.UsoIA).filter(
        models.UsoIA.produto_id == produto_id,
        models.UsoIA.user_id == user_id # Garante que o usuário só veja os seus
    ).order_by(models.UsoIA.timestamp.desc()).offset(skip).limit(limit).all()
    
def get_all_usos_ia_admin(db: Session, skip: int = 0, limit: int = 100) -> List[models.UsoIA]:
    return db.query(models.UsoIA).order_by(models.UsoIA.timestamp.desc()).offset(skip).limit(limit).all()


# --- ProductType CRUD ---

def create_product_type(db: Session, product_type: schemas.ProductTypeCreate, user_id: Optional[int] = None) -> models.ProductType:
    """
    Cria um novo tipo de produto.
    Se user_id for fornecido, o tipo é associado a esse usuário.
    Se user_id for None, o tipo é considerado global.
    """
    db_product_type = models.ProductType(
        **product_type.model_dump(),
        user_id=user_id  # Pode ser None para tipos globais
    )
    db.add(db_product_type)
    db.commit()
    db.refresh(db_product_type)
    # Eager load attribute_templates para consistência com ProductTypeRead
    # Isso garante que, mesmo que não haja templates, o campo esteja presente.
    if not hasattr(db_product_type, 'attribute_templates') or db_product_type.attribute_templates is None:
         db.refresh(db_product_type, attribute_names=['attribute_templates']) # Carrega se não estiver carregado
    return db_product_type

def get_product_type(db: Session, product_type_id: int) -> Optional[models.ProductType]:
    """
    Obtém um tipo de produto específico pelo ID, incluindo seus templates de atributo.
    """
    return db.query(models.ProductType).options(
        selectinload(models.ProductType.attribute_templates)
    ).filter(models.ProductType.id == product_type_id).first()

def get_product_type_by_key_name(db: Session, key_name: str) -> Optional[models.ProductType]:
    """
    Obtém um tipo de produto específico pelo nome chave (key_name), incluindo seus templates de atributo.
    """
    return db.query(models.ProductType).options(
        selectinload(models.ProductType.attribute_templates)
    ).filter(models.ProductType.key_name == key_name).first()

def get_product_types(db: Session, skip: int = 0, limit: int = 100, for_user_id: Optional[int] = None) -> List[models.ProductType]:
    """
    Lista tipos de produto com paginação, incluindo seus templates de atributo.
    - Se 'for_user_id' é fornecido, lista os tipos desse usuário E os tipos globais (user_id IS NULL).
    - Se 'for_user_id' é None, lista APENAS os tipos globais.
    """
    query = db.query(models.ProductType).options(
        selectinload(models.ProductType.attribute_templates) # Garante que os templates são carregados
    )
    if for_user_id is not None:
        query = query.filter(
            or_(
                models.ProductType.user_id == for_user_id,
                models.ProductType.user_id == None  # Tipos globais
            )
        )
    else:
        # Apenas tipos globais se nenhum usuário específico for solicitado
        query = query.filter(models.ProductType.user_id == None)
    
    return query.order_by(models.ProductType.friendly_name).offset(skip).limit(limit).all()

def get_all_product_types_admin(db: Session, skip: int = 0, limit: int = 100) -> List[models.ProductType]:
    """
    Lista TODOS os tipos de produto (para administradores), incluindo templates de atributo.
    """
    return db.query(models.ProductType).options(
        selectinload(models.ProductType.attribute_templates)
    ).order_by(models.ProductType.id).offset(skip).limit(limit).all()


def update_product_type(db: Session, db_product_type: models.ProductType, product_type_update: schemas.ProductTypeUpdate) -> models.ProductType:
    """
    Atualiza um tipo de produto existente.
    """
    update_data = product_type_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product_type, key, value)
    db.commit()
    db.refresh(db_product_type)
    # Eager load attribute_templates para consistência com ProductTypeRead
    if not hasattr(db_product_type, 'attribute_templates') or db_product_type.attribute_templates is None: # pragma: no cover
         db.refresh(db_product_type, attribute_names=['attribute_templates']) # Carrega se não estiver carregado
    return db_product_type

def delete_product_type(db: Session, db_product_type: models.ProductType):
    """
    Deleta um tipo de produto.
    Os AttributeTemplates associados serão deletados em cascata devido à configuração no modelo.
    """
    db.delete(db_product_type)
    db.commit()
    return # Retorna None, pois o objeto foi deletado.


# --- AttributeTemplate CRUD ---

def get_attribute_template(db: Session, attribute_template_id: int, product_type_id: Optional[int] = None) -> Optional[models.AttributeTemplate]:
    """
    Obtém um template de atributo específico pelo seu ID.
    Se product_type_id for fornecido, verifica se o atributo pertence a esse tipo de produto.
    """
    query = db.query(models.AttributeTemplate).filter(models.AttributeTemplate.id == attribute_template_id)
    if product_type_id is not None:
        query = query.filter(models.AttributeTemplate.product_type_id == product_type_id)
    return query.first()

def get_attribute_templates_for_product_type(db: Session, product_type_id: int, skip: int = 0, limit: int = 100) -> List[models.AttributeTemplate]:
    """
    Lista todos os templates de atributo para um ProductType específico.
    """
    return db.query(models.AttributeTemplate).filter(
        models.AttributeTemplate.product_type_id == product_type_id
    ).order_by(models.AttributeTemplate.display_order, models.AttributeTemplate.label).offset(skip).limit(limit).all()

def create_attribute_template(db: Session, attribute_template: schemas.AttributeTemplateCreate, product_type_id: int) -> models.AttributeTemplate:
    """
    Cria um novo template de atributo para um ProductType específico.
    """
    # Verifica se o ProductType existe
    product_type = db.query(models.ProductType).filter(models.ProductType.id == product_type_id).first()
    if not product_type:
        # Você pode querer levantar uma exceção aqui ou deixar o router tratar
        return None 

    db_attribute_template = models.AttributeTemplate(
        **attribute_template.model_dump(),
        product_type_id=product_type_id
    )
    db.add(db_attribute_template)
    db.commit()
    db.refresh(db_attribute_template)
    return db_attribute_template

def update_attribute_template(
    db: Session, 
    db_attribute_template: models.AttributeTemplate, 
    attribute_template_update: schemas.AttributeTemplateUpdate
) -> models.AttributeTemplate:
    """
    Atualiza um template de atributo existente.
    """
    update_data = attribute_template_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_attribute_template, key, value)
    db.commit()
    db.refresh(db_attribute_template)
    return db_attribute_template

def delete_attribute_template(db: Session, db_attribute_template: models.AttributeTemplate):
    """
    Deleta um template de atributo.
    """
    db.delete(db_attribute_template)
    db.commit()
    return # Retorna None

# --- FIM DAS FUNÇÕES CRUD PARA ATTRIBUTETEMPLATE ---