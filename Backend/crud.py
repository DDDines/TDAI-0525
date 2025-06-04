# Backend/crud.py
import logging
import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, and_, desc, asc, extract # Adicionado extract
from sqlalchemy.orm import Session, joinedload, selectinload, aliased
from sqlalchemy.exc import IntegrityError

from jose import jwt # Para decodificar token se necessário (ex: social_auth)

from core.config import settings # Para JWT_SECRET_KEY, ALGORITHM, etc.
from core import security # Para hash de senha
from models import ( # Isso está correto
    User, Role, Plano, Produto, Fornecedor, ProductType, AttributeTemplate, RegistroUsoIA,
    StatusEnriquecimentoEnum, StatusGeracaoIAEnum, TipoAcaoIAEnum, AttributeFieldTypeEnum
)
import Project.Backend.schemas as schemas # Importa todos os schemas

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> User:
    hashed_password = security.get_password_hash(user.password)
    
    # Define os limites iniciais baseados nas configurações padrão para usuários sem plano
    default_limite_produtos = settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO
    default_limite_enriquecimento = settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO
    default_limite_geracao_ia = settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO
    
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        nome_completo=user.nome_completo,
        idioma_preferido=user.idioma_preferido,
        chave_openai_pessoal=user.chave_openai_pessoal,
        chave_google_gemini_pessoal=user.chave_google_gemini_pessoal,
        limite_produtos=default_limite_produtos,
        limite_enriquecimento_web=default_limite_enriquecimento,
        limite_geracao_ia=default_limite_geracao_ia,
        is_active=True, # Usuários são ativos por padrão na criação normal
        is_superuser=False # Superuser só é definido explicitamente
    )

    if user.plano_id:
        plano = get_plano(db, plano_id=user.plano_id)
        if plano:
            db_user.plano_id = plano.id
            db_user.limite_produtos = plano.limite_produtos
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano.limite_geracao_ia
            # data_expiracao_plano pode ser definida aqui se for relevante (ex: +30 dias)
            # db_user.data_expiracao_plano = datetime.now(timezone.utc) + timedelta(days=30)
        else:
            logger.warning(f"Plano com ID {user.plano_id} não encontrado ao criar usuário {user.email}. Usando defaults.")
            # Mantém os limites default caso o plano não seja encontrado (embora a validação deva ocorrer no router)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: User, user_update: Union[schemas.UserUpdate, schemas.UserUpdateByAdmin, schemas.UserUpdateOAuth]) -> User:
    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        hashed_password = security.get_password_hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"] # Evita que seja atribuído diretamente no loop

    # Atualizar plano e limites associados
    if "plano_id" in update_data:
        new_plano_id = update_data["plano_id"]
        if new_plano_id is None: # Usuário está removendo o plano
            db_user.plano_id = None
            db_user.limite_produtos = settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO
            db_user.limite_enriquecimento_web = settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO
            db_user.limite_geracao_ia = settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO
            db_user.data_expiracao_plano = None
        else:
            plano = get_plano(db, plano_id=new_plano_id)
            if plano:
                db_user.plano_id = plano.id
                db_user.limite_produtos = plano.limite_produtos
                db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
                db_user.limite_geracao_ia = plano.limite_geracao_ia
                # db_user.data_expiracao_plano = datetime.now(timezone.utc) + timedelta(days=30) # ou outra lógica
            else:
                # Se o plano não for encontrado, talvez não atualizar ou logar um erro.
                # Por ora, não altera o plano se o ID for inválido e não for None.
                logger.warning(f"Plano com ID {new_plano_id} não encontrado ao atualizar usuário {db_user.email}. Plano não alterado.")
        # Remove plano_id de update_data para não ser processado no loop abaixo,
        # pois os limites são tratados separadamente aqui ou via UserUpdateByAdmin.
        if "plano_id" in update_data: # precisa verificar novamente pois UserUpdateOAuth pode não ter
            del update_data["plano_id"]


    # Para campos que podem ser atualizados diretamente
    for field, value in update_data.items():
        if hasattr(db_user, field):
            setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, db_user: User) -> User:
    db.delete(db_user)
    db.commit()
    return db_user

def create_user_oauth(db: Session, user_oauth: schemas.UserCreateOAuth, plano_id_default: Optional[int] = None) -> User:
    db_user = User(
        email=user_oauth.email,
        nome_completo=user_oauth.nome_completo,
        provider=user_oauth.provider,
        provider_user_id=user_oauth.provider_user_id,
        is_active=True,
        idioma_preferido=user_oauth.idioma_preferido, # Adicionado
        # Limites padrão, serão atualizados se plano_id_default for fornecido
        limite_produtos=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO,
        limite_enriquecimento_web=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO,
        limite_geracao_ia=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO,
    )
    if plano_id_default:
        plano = get_plano(db, plano_id=plano_id_default)
        if plano:
            db_user.plano_id = plano.id
            db_user.limite_produtos = plano.limite_produtos
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano.limite_geracao_ia
            # db_user.data_expiracao_plano = datetime.now(timezone.utc) + timedelta(days=30) # Exemplo
    
    # Se o Role padrão "user" existir, atribui-lo
    default_role = get_role_by_name(db, "user")
    if default_role:
        db_user.role_id = default_role.id

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_provider(db: Session, provider: str, provider_user_id: str) -> Optional[User]:
    return db.query(User).filter(User.provider == provider, User.provider_user_id == provider_user_id).first()


def set_user_password_reset_token(db: Session, user: User, token: str, expires_at: datetime) -> None:
    user.reset_password_token = token
    user.reset_password_token_expires_at = expires_at
    db.commit()
    db.refresh(user)

def get_user_by_reset_token(db: Session, token: str) -> Optional[User]:
    return db.query(User).filter(User.reset_password_token == token).first()

# --- Role CRUD ---
def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()

def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()

def get_roles(db: Session, skip: int = 0, limit: int = 10) -> List[Role]:
    return db.query(Role).offset(skip).limit(limit).all()

def create_role(db: Session, role: schemas.RoleCreate) -> Role:
    db_role = Role(name=role.name, description=role.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

# --- Plano CRUD ---
def get_plano(db: Session, plano_id: int) -> Optional[Plano]:
    return db.query(Plano).filter(Plano.id == plano_id).first()

def get_plano_by_name(db: Session, nome: str) -> Optional[Plano]:
    return db.query(Plano).filter(Plano.nome == nome).first()

def get_planos(db: Session, skip: int = 0, limit: int = 10) -> List[Plano]:
    return db.query(Plano).offset(skip).limit(limit).all()

def create_plano(db: Session, plano: schemas.PlanoCreate) -> Plano:
    db_plano = Plano(**plano.model_dump())
    db.add(db_plano)
    db.commit()
    db.refresh(db_plano)
    return db_plano

def update_plano(db: Session, db_plano: Plano, plano_update: schemas.PlanoUpdate) -> Plano:
    update_data = plano_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_plano, key, value)
    db.commit()
    db.refresh(db_plano)
    return db_plano

def delete_plano(db: Session, db_plano: Plano):
    db.delete(db_plano)
    db.commit()
    return db_plano


# --- Fornecedor CRUD ---
def create_fornecedor(db: Session, fornecedor: schemas.FornecedorCreate, user_id: int) -> Fornecedor:
    db_fornecedor = Fornecedor(**fornecedor.model_dump(), user_id=user_id)
    db.add(db_fornecedor)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor

def get_fornecedor(db: Session, fornecedor_id: int) -> Optional[Fornecedor]:
    return db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id).first()

def get_fornecedores_by_user(
    db: Session,
    user_id: Optional[int] = None, # Tornar opcional para admins
    is_admin: bool = False,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None
) -> List[Fornecedor]:
    query = db.query(Fornecedor)
    if not is_admin and user_id:
        query = query.filter(Fornecedor.user_id == user_id)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Fornecedor.nome).ilike(search_term),
                func.lower(Fornecedor.email_contato).ilike(search_term), # Ajustado para email_contato
                func.lower(Fornecedor.contato_principal).ilike(search_term) # Ajustado para contato_principal
            )
        )
    return query.order_by(Fornecedor.nome).offset(skip).limit(limit).all()


def count_fornecedores_by_user(
    db: Session,
    user_id: Optional[int] = None, # Tornar opcional para admins
    is_admin: bool = False,
    search: Optional[str] = None
) -> int:
    query = db.query(func.count(Fornecedor.id))
    if not is_admin and user_id:
        query = query.filter(Fornecedor.user_id == user_id)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Fornecedor.nome).ilike(search_term),
                func.lower(Fornecedor.email_contato).ilike(search_term),
                func.lower(Fornecedor.contato_principal).ilike(search_term)
            )
        )
    return query.scalar() or 0


def update_fornecedor(db: Session, db_fornecedor: Fornecedor, fornecedor_update: schemas.FornecedorUpdate) -> Fornecedor:
    update_data = fornecedor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_fornecedor, key, value)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor

def delete_fornecedor(db: Session, db_fornecedor: Fornecedor) -> Fornecedor:
    db.delete(db_fornecedor)
    db.commit()
    # Se Fornecedor não tiver cascade para produtos, a referência em produto precisa ser tratada (setar para None)
    # No seu model.py, Produto tem um relacionamento com Fornecedor, mas Fornecedor não tem cascade="all, delete-orphan" para Produto.
    # Isso significa que deletar um fornecedor não deleta os produtos.
    # A ForeignKey `fornecedor_id` em `Produto` deve ser `nullable=True` e `ondelete="SET NULL"` no DB,
    # ou você precisa fazer isso manualmente:
    # db.query(Produto).filter(Produto.fornecedor_id == db_fornecedor.id).update({"fornecedor_id": None})
    # db.commit()
    # No entanto, a lógica atual do seu `models.Produto` para `fornecedor_id` é `nullable=True`
    # o que é bom. O `ondelete` no DB é o mais robusto.
    return db_fornecedor


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


# --- Produto CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate, user_id: int) -> Produto:
    # Converte dynamic_attributes para dict se for string JSON
    # dynamic_attrs_dict = {}
    # if produto.dynamic_attributes:
    #     if isinstance(produto.dynamic_attributes, str):
    #         try:
    #             dynamic_attrs_dict = json.loads(produto.dynamic_attributes)
    #         except json.JSONDecodeError:
    #             raise ValueError("Dynamic attributes não é um JSON válido.")
    #     elif isinstance(produto.dynamic_attributes, dict):
    #         dynamic_attrs_dict = produto.dynamic_attributes
    #     else:
    #         raise ValueError("Dynamic attributes deve ser um JSON string ou um dict.")

    # dados_brutos_dict = {}
    # if produto.dados_brutos:
    #     if isinstance(produto.dados_brutos, str):
    #         try:
    #             dados_brutos_dict = json.loads(produto.dados_brutos)
    #         except json.JSONDecodeError:
    #             raise ValueError("Dados brutos não são um JSON válido.")
    #     elif isinstance(produto.dados_brutos, dict):
    #         dados_brutos_dict = produto.dados_brutos
    #     else:
    #         raise ValueError("Dados brutos devem ser um JSON string ou um dict.")
            
    # Pydantic v2 com Json[Type] já deve lidar com a conversão no schema.
    # O modelo SQLAlchemy espera um dict para colunas JSON.

    produto_data = produto.model_dump(exclude_unset=True)
    
    # Assegura que campos JSON estejam como dicts
    if 'dynamic_attributes' in produto_data and isinstance(produto_data['dynamic_attributes'], str):
        try:
            produto_data['dynamic_attributes'] = json.loads(produto_data['dynamic_attributes'])
        except json.JSONDecodeError:
            raise ValueError("dynamic_attributes não é um JSON string válido.")
            
    if 'dados_brutos' in produto_data and isinstance(produto_data['dados_brutos'], str):
        try:
            produto_data['dados_brutos'] = json.loads(produto_data['dados_brutos'])
        except json.JSONDecodeError:
            raise ValueError("dados_brutos não é um JSON string válido.")

    # Se imagens_secundarias_urls for uma string JSON, converter para lista
    # (Pydantic List[HttpUrl] deve tratar isso na entrada se o cliente enviar JSON string,
    # mas se for de um form multipart, pode precisar de tratamento especial no router)
    # if 'imagens_secundarias_urls' in produto_data and isinstance(produto_data['imagens_secundarias_urls'], str):
    # try:
    #         parsed_urls = json.loads(produto_data['imagens_secundarias_urls'])
    # if isinstance(parsed_urls, list):
    #             produto_data['imagens_secundarias_urls'] = parsed_urls
    # else:
    # raise ValueError("imagens_secundarias_urls deve ser uma lista de URLs.")
    # except json.JSONDecodeError:
    # raise ValueError("imagens_secundarias_urls não é um JSON string válido representando uma lista.")


    db_produto = Produto(**produto_data, user_id=user_id)
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto


def get_produto(db: Session, produto_id: int) -> Optional[Produto]:
    # Usar selectinload para carregar relacionamentos de forma eficiente se sempre forem acessados
    return db.query(Produto).options(
        selectinload(Produto.fornecedor),
        selectinload(Produto.product_type).selectinload(ProductType.attribute_templates)
    ).filter(Produto.id == produto_id).first()


def get_produtos_by_user(
    db: Session,
    user_id: Optional[int], # Se None e is_admin=True, busca todos. Se user_id e is_admin=False, busca do usuário.
    is_admin: bool,
    skip: int = 0,
    limit: int = 10,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    search: Optional[str] = None,
    fornecedor_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    categoria: Optional[str] = None, # Adicionado
    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None, # Adicionado
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = None, # Adicionado
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = None # Adicionado
) -> List[Produto]:
    query = db.query(Produto).options(
        selectinload(Produto.fornecedor),
        selectinload(Produto.product_type) # Carrega product_type, mas não seus atributos aqui para a lista
    )

    if not is_admin:
        if user_id is None: # Não deveria acontecer se não for admin e não tiver user_id
            return []
        query = query.filter(Produto.user_id == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Produto.nome_base).ilike(search_term),
                func.lower(Produto.nome_chat_api).ilike(search_term),
                func.lower(Produto.descricao_original).ilike(search_term),
                func.lower(Produto.descricao_chat_api).ilike(search_term),
                func.lower(Produto.sku).ilike(search_term),
                func.lower(Produto.ean).ilike(search_term),
                func.lower(Produto.marca).ilike(search_term),
                func.lower(Produto.modelo).ilike(search_term)
            )
        )
    
    if fornecedor_id is not None:
        query = query.filter(Produto.fornecedor_id == fornecedor_id)
    if product_type_id is not None:
        query = query.filter(Produto.product_type_id == product_type_id)
    if categoria:
        query = query.filter(func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%")) # Ou categoria_mapeada
    if status_enriquecimento_web:
        query = query.filter(Produto.status_enriquecimento_web == status_enriquecimento_web)
    if status_titulo_ia:
        query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(Produto.status_descricao_ia == status_descricao_ia)

    if sort_by:
        column_to_sort = getattr(Produto, sort_by, None)
        if column_to_sort:
            if sort_order.lower() == "desc":
                query = query.order_by(desc(column_to_sort))
            else:
                query = query.order_by(asc(column_to_sort))
        else: # Fallback ou log de erro se sort_by for inválido
            query = query.order_by(Produto.id) 
    else:
        query = query.order_by(Produto.id) # Ordenação padrão

    return query.offset(skip).limit(limit).all()


def count_produtos_by_user(
    db: Session,
    user_id: Optional[int],
    is_admin: bool,
    search: Optional[str] = None,
    fornecedor_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    categoria: Optional[str] = None,
    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None,
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = None,
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = None
) -> int:
    query = db.query(func.count(Produto.id))

    if not is_admin:
        if user_id is None:
            return 0
        query = query.filter(Produto.user_id == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
             or_(
                func.lower(Produto.nome_base).ilike(search_term),
                func.lower(Produto.nome_chat_api).ilike(search_term),
                func.lower(Produto.descricao_original).ilike(search_term),
                func.lower(Produto.descricao_chat_api).ilike(search_term),
                func.lower(Produto.sku).ilike(search_term),
                func.lower(Produto.ean).ilike(search_term),
                func.lower(Produto.marca).ilike(search_term),
                func.lower(Produto.modelo).ilike(search_term)
            )
        )
    if fornecedor_id is not None:
        query = query.filter(Produto.fornecedor_id == fornecedor_id)
    if product_type_id is not None:
        query = query.filter(Produto.product_type_id == product_type_id)
    if categoria:
        query = query.filter(func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%"))
    if status_enriquecimento_web:
        query = query.filter(Produto.status_enriquecimento_web == status_enriquecimento_web)
    if status_titulo_ia:
        query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(Produto.status_descricao_ia == status_descricao_ia)
        
    count = query.scalar()
    return count if count is not None else 0

def update_produto(db: Session, db_produto: Produto, produto_update: schemas.ProdutoUpdate) -> Produto:
    update_data = produto_update.model_dump(exclude_unset=True)

    # Lógica para campos JSON (dynamic_attributes, dados_brutos, imagens_secundarias_urls)
    # Pydantic deve entregar dict/list se o schema estiver correto (não Json[Type])
    # O modelo SQLAlchemy aceita dict/list para colunas JSON.
    for field in ['dynamic_attributes', 'dados_brutos', 'imagens_secundarias_urls']:
        if field in update_data and update_data[field] is not None:
            # Se o schema já garante o tipo correto (dict/list), apenas atribua
            # Se o schema ainda for Json[Type] e vier uma string, precisa de json.loads aqui
            # Assumindo que o schema.ProdutoUpdate terá Dict/List para esses campos:
            pass # setattr abaixo cuidará disso

    for key, value in update_data.items():
        setattr(db_produto, key, value)
    
    db.commit()
    db.refresh(db_produto)
    # Recarregar relacionamentos se forem modificados ou para garantir consistência na resposta
    db.refresh(db_produto, attribute_names=['fornecedor', 'product_type'])
    if db_produto.product_type: # Para garantir que os atributos do tipo também sejam carregados se product_type for acessado
        db.refresh(db_produto.product_type, attribute_names=['attribute_templates'])
    return db_produto


def delete_produto(db: Session, db_produto: Produto) -> Produto:
    # Antes de deletar, pode ser necessário limpar referências em RegistroUsoIA se não houver cascade
    # No seu modelo, RegistroUsoIA tem cascade="all, delete-orphan" para produto, então está OK.
    db.delete(db_produto)
    db.commit()
    return db_produto

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
        RegistroUsoIA.tipo_acao.not_in([TipoAcaoIAEnum.ENRIQUECIMENTO_WEB_PRODUTO]) # Exclui enriquecimento
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
    
    # Se houveram usos por usuários sem plano E não foi capturado por um plano NULL no join
    # (o outerjoin deveria capturar PlanoInfo.id como None, mas a query agrupa por PlanoInfo.id)
    # A melhor forma é um count separado e adicionar se > 0
    if count_sem_plano > 0:
        # Verificar se "Sem Plano" já está na lista (caso o outerjoin tenha funcionado com plano_id=None)
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
                    item["total_geracoes_ia_no_mes"] = count_sem_plano # Assume que a query principal pode não pegar todos
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
    """
    Retorna usuários ativos com algumas informações de atividade.
    Esta é uma função de exemplo, pode precisar de mais otimizações ou campos.
    """
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
    
    # O resultado é uma lista de tuplas (User, total_produtos, total_geracoes_ia_mes_corrente)
    # Precisamos transformar isso para que o schema UserActivity possa ser populado.
    # O schema UserActivity espera atributos no objeto principal.
    # Uma forma é adicionar esses atributos dinamicamente ao objeto User antes de retornar.
    
    user_activity_list = []
    for user_model, total_prods, total_ia in users:
        # Criar um dicionário para popular UserActivity schema
        activity_data = {
            "user_id": user_model.id,
            "email": user_model.email,
            "nome_completo": user_model.nome_completo,
            "created_at": user_model.created_at,
            "total_produtos": total_prods or 0,
            "total_geracoes_ia_mes_corrente": total_ia or 0,
        }
        # Isso não é ideal para popular um schema `from_attributes` diretamente do user_model
        # se o schema espera os campos de contagem como atributos do User.
        # Em vez disso, retornamos o objeto User e o router constrói o UserActivity.
        # Ou, o schema UserActivity deve ser construído a partir de um dict.
        
        # Por agora, vamos adicionar dinamicamente, mas isso pode não ser a melhor prática.
        setattr(user_model, 'total_produtos_count', total_prods or 0) # Nome diferente para não colidir
        setattr(user_model, 'total_geracoes_ia_mes_corrente_count', total_ia or 0)
        user_activity_list.append(user_model)

    # return user_activity_list
    # O router /admin/analytics/user-activity espera uma lista de schemas.UserActivity
    # É melhor construir o schema no router a partir dos dados.
    # A função CRUD deve retornar os dados brutos ou objetos do modelo.

    return users # Retorna a lista de tuplas (User, count1, count2)


# Função auxiliar para o startup (main.py)
def create_initial_data(db: Session):
    logger.info("Verificando/criando dados iniciais (roles, planos, admin)...")
    
    # Criar Roles Padrão
    roles_padrao = [
        {"name": "admin", "description": "Administrador do sistema"},
        {"name": "user", "description": "Usuário padrão da plataforma"},
        # {"name": "gerente", "description": "Usuário com permissões de gerenciamento de equipe"},
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
        # Atribuir plano Pro ao admin como exemplo, ou um plano específico de admin
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
        logger.info(f"Usuário administrador '{admin_email}' criado com sucesso.")
    else:
        logger.info(f"Usuário administrador '{admin_email}' já existe (ID: {admin_user.id}, Superuser: {admin_user.is_superuser}, Role ID: {admin_user.role_id}, Plano ID: {admin_user.plano_id}).")


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
                    options=["P", "M", "G", "GG"],   # Correto: lista Python!
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
                    options=["Masculino", "Feminino", "Unissex"],  # Correto: lista Python!
                    display_order=4
                ),
            ]
        }
    ]

    for pt_data in tipos_produto_globais:
        # pt_schema = schemas.ProductTypeCreate(**{k:v for k,v in pt_data.items() if k != 'attribute_templates'})
        # attr_schemas = [schemas.AttributeTemplateCreate(**attr) for attr in pt_data.get("attribute_templates", [])]
        
        # Criando o schema Pydantic corretamente
        attr_template_schemas = [schemas.AttributeTemplateCreate(**attr) for attr in pt_data.get("attribute_templates", [])]
        pt_create_schema = schemas.ProductTypeCreate(
            key_name=pt_data["key_name"],
            friendly_name=pt_data["friendly_name"],
            description=pt_data.get("description"),
            attribute_templates=attr_template_schemas
        )

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

    logger.info("Criação/verificação de dados iniciais concluída.")