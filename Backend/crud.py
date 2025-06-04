# Backend/crud.py
from typing import List, Optional, Union, Dict, Any
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, and_, desc, asc, select
from sqlalchemy.exc import SQLAlchemyError 
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
import shutil 
import secrets 
from datetime import datetime, timezone, timedelta 
import enum 
from pydantic import HttpUrl # Não usado diretamente aqui, mas pode estar em schemas

import models
import schemas
from core.config import pwd_context, settings 


# Utils
UPLOAD_DIRECTORY = Path(settings.UPLOAD_DIRECTORY) 
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"} 

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(func.lower(models.User.email) == func.lower(email)).first() 

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate, plano_id: Optional[int] = None, role_id: Optional[int] = None) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user_data = {
        "email": user.email.lower(),
        "hashed_password": hashed_password,
        "nome_completo": user.nome_completo, 
        "idioma_preferido": user.idioma_preferido,
        "is_active": True,
        "is_superuser": False, # Definido como False por padrão
        "chave_openai_pessoal": user.chave_openai_pessoal,
        "chave_google_gemini_pessoal": user.chave_google_gemini_pessoal
    }
    if role_id:
        db_user_data["role_id"] = role_id

    db_user = models.User(**db_user_data)

    # Determina o plano_id efetivo
    effective_plano_id = user.plano_id if hasattr(user, 'plano_id') and user.plano_id is not None else plano_id
    
    if effective_plano_id:
        plano = get_plano(db, plano_id=effective_plano_id)
        if not plano:
            # Se o plano especificado não for encontrado, atribui o gratuito como fallback
            print(f"AVISO CRUD: Plano com ID {effective_plano_id} não encontrado ao criar usuário. Tentando atribuir plano Gratuito.")
            plano_gratuito = get_plano_by_nome(db, nome="Gratuito")
            if plano_gratuito:
                db_user.plano = plano_gratuito
                db_user.plano_id = plano_gratuito.id
                db_user.limite_produtos = plano_gratuito.limite_produtos
                db_user.limite_enriquecimento_web = plano_gratuito.limite_enriquecimento_web
                db_user.limite_geracao_ia = plano_gratuito.limite_geracao_ia
            else:
                print("ERRO CRUD: Plano Gratuito não encontrado. Usuário será criado sem limites de plano definidos.")
                # Considerar se deve levantar uma exceção aqui ou permitir usuário sem plano
        else:
            db_user.plano = plano
            db_user.plano_id = plano.id 
            db_user.limite_produtos = plano.limite_produtos
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano.limite_geracao_ia
    else: # Se nenhum plano_id foi fornecido, atribui o gratuito
        plano_gratuito = get_plano_by_nome(db, nome="Gratuito") 
        if plano_gratuito:
            db_user.plano = plano_gratuito
            db_user.plano_id = plano_gratuito.id
            db_user.limite_produtos = plano_gratuito.limite_produtos
            db_user.limite_enriquecimento_web = plano_gratuito.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano_gratuito.limite_geracao_ia
        else:
            print("ERRO CRUD: Plano Gratuito padrão não encontrado. Usuário será criado sem limites de plano definidos.")
            
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update_data: Union[schemas.UserUpdate, schemas.UserUpdateByAdmin, schemas.UserUpdateOAuth]) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    update_data = user_update_data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"]
    
    if "email" in update_data and db_user.email: # Adicionado db_user.email para garantir que não seja None
        update_data["email"] = update_data["email"].lower()

    if "plano_id" in update_data:
        plano_id = update_data.pop("plano_id") 
        if plano_id is None: # Se o plano_id for explicitamente None, remove o plano
            db_user.plano_id = None
            db_user.plano = None # Remove a relação
            # Aplica limites padrão se o usuário ficar sem plano
            db_user.limite_produtos = settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO 
            db_user.limite_enriquecimento_web = settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO
            db_user.limite_geracao_ia = settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO
            db_user.data_expiracao_plano = None # Reseta data de expiração se houver
        else:
            plano = get_plano(db, plano_id=plano_id)
            if not plano:
                raise HTTPException(status_code=404, detail=f"Plano com ID {plano_id} não encontrado.")
            db_user.plano = plano 
            db_user.plano_id = plano.id 
            db_user.limite_produtos = plano.limite_produtos
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano.limite_geracao_ia
            # Lógica para data_expiracao_plano deve ser tratada à parte, se aplicável
            # Por exemplo, se o plano for 'Pro Anual', definir a expiração.
            # if plano.nome == "Pro Anual":
            # db_user.data_expiracao_plano = datetime.now(timezone.utc) + timedelta(days=365)
            # else:
            # db_user.data_expiracao_plano = None

    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    if hasattr(db_user, 'updated_at') and db.is_modified(db_user): 
        db_user.updated_at = datetime.now(timezone.utc) 
    
    try:
        db.commit()
        db.refresh(db_user)
    except SQLAlchemyError as e_sql_commit:
        db.rollback()
        print(f"ERRO CRUD SQL ao commitar atualização do usuário ID {db_user.id}: {e_sql_commit}")
        # Não relançar HTTPException aqui diretamente pode ser melhor para desacoplar
        # A camada de serviço/rota pode tratar o erro e levantar HTTPException
        raise # Ou raise uma exceção customizada
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user: return None
    db.delete(db_user)
    db.commit()
    return db_user # O objeto ainda está em memória, mas deletado do DB

def create_user_oauth(db: Session, user_data: schemas.UserCreateOAuth, plano_id: Optional[int] = None) -> models.User:
    db_user = models.User(
        email=user_data.email.lower(),
        nome_completo=user_data.nome_completo, 
        provider=user_data.provider, 
        provider_user_id=user_data.provider_user_id, 
        is_active=True,  
        is_superuser=False, 
        hashed_password=None # Usuários OAuth podem não ter senha local inicialmente
    )
    if plano_id: 
        plano = get_plano(db, plano_id=plano_id) 
        if plano: 
            db_user.plano = plano 
            db_user.plano_id = plano.id 
            db_user.limite_produtos = plano.limite_produtos 
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web 
            db_user.limite_geracao_ia = plano.limite_geracao_ia 
    else: 
        plano_gratuito = get_plano_by_nome(db, nome="Gratuito")  
        if plano_gratuito: 
            db_user.plano = plano_gratuito 
            db_user.plano_id = plano_gratuito.id 
            db_user.limite_produtos = plano_gratuito.limite_produtos 
            db_user.limite_enriquecimento_web = plano_gratuito.limite_enriquecimento_web 
            db_user.limite_geracao_ia = plano_gratuito.limite_geracao_ia 
    db.add(db_user) 
    db.commit() 
    db.refresh(db_user) 
    return db_user 

def update_user_password_reset_token(db: Session, user_id: int, token: Optional[str], expires_at: Optional[datetime]) -> Optional[models.User]: 
    db_user = get_user(db, user_id) 
    if db_user: 
        db_user.reset_password_token = token 
        db_user.reset_password_token_expires_at = expires_at 
        db.commit() 
        db.refresh(db_user) 
    return db_user 

def get_user_by_reset_token(db: Session, token: str) -> Optional[models.User]: 
    return db.query(models.User).filter(
        models.User.reset_password_token == token,
        models.User.reset_password_token_expires_at > datetime.now(timezone.utc) # Verifica expiração
    ).first()

# --- Role CRUD ---
def get_role_by_name(db: Session, name: str) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.name == name).first()

def get_role(db: Session, role_id: int) -> Optional[models.Role]:
    return db.query(models.Role).filter(models.Role.id == role_id).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[models.Role]:
    return db.query(models.Role).order_by(models.Role.name).offset(skip).limit(limit).all()

def create_role(db: Session, role: schemas.RoleCreate) -> models.Role:
    db_role = models.Role(**role.model_dump())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

# --- Plano CRUD ---
def get_plano_by_nome(db: Session, nome: str) -> Optional[models.Plano]:
    return db.query(models.Plano).filter(func.lower(models.Plano.nome) == func.lower(nome)).first() 

def get_plano(db: Session, plano_id: int) -> Optional[models.Plano]:
    return db.query(models.Plano).filter(models.Plano.id == plano_id).first()

def get_planos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Plano]:
    return db.query(models.Plano).order_by(models.Plano.id).offset(skip).limit(limit).all()

def create_plano(db: Session, plano: schemas.PlanoCreate) -> models.Plano:
    db_plano = models.Plano(**plano.model_dump())
    db.add(db_plano)
    db.commit()
    db.refresh(db_plano)
    return db_plano

# --- Fornecedor CRUD ---
def create_fornecedor(db: Session, fornecedor: schemas.FornecedorCreate, user_id: int) -> models.Fornecedor:
    existing_fornecedor = db.query(models.Fornecedor).filter(
        models.Fornecedor.user_id == user_id,
        func.lower(models.Fornecedor.nome) == func.lower(fornecedor.nome)
    ).first()
    if existing_fornecedor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fornecedor com o nome '{fornecedor.nome}' já existe para este usuário."
        )
    
    fornecedor_data = fornecedor.model_dump(exclude_unset=True) 
    if fornecedor_data.get("site_url") is not None: # Converte HttpUrl para string
        fornecedor_data["site_url"] = str(fornecedor_data["site_url"])
    if fornecedor_data.get("link_busca_padrao") is not None: # Converte HttpUrl para string
        fornecedor_data["link_busca_padrao"] = str(fornecedor_data["link_busca_padrao"])
        
    db_fornecedor = models.Fornecedor(**fornecedor_data, user_id=user_id)
    db.add(db_fornecedor)
    try:
        db.commit()
        db.refresh(db_fornecedor)
    except SQLAlchemyError as e_sql_commit: # Erro mais específico
        db.rollback()
        # Logar o erro e_sql_commit seria útil aqui
        print(f"ERRO CRUD SQL create_fornecedor: {e_sql_commit}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar fornecedor no banco de dados.")
    return db_fornecedor

def get_fornecedor(db: Session, fornecedor_id: int, user_id: Optional[int] = None) -> Optional[models.Fornecedor]:
    query = db.query(models.Fornecedor).filter(models.Fornecedor.id == fornecedor_id)
    if user_id is not None: # Filtra por user_id se fornecido (para checagem de permissão na rota)
        query = query.filter(models.Fornecedor.user_id == user_id)
    return query.first()

def get_fornecedores_by_user(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    termo_busca: Optional[str] = None # Corrigido para termo_busca
) -> List[models.Fornecedor]:
    query = db.query(models.Fornecedor).filter(models.Fornecedor.user_id == user_id)
    if termo_busca:
        query = query.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    return query.order_by(models.Fornecedor.nome).offset(skip).limit(limit).all()

def count_fornecedores_by_user(db: Session, user_id: int, termo_busca: Optional[str] = None) -> int:
    query = db.query(func.count(models.Fornecedor.id)).filter(models.Fornecedor.user_id == user_id)
    if termo_busca:
        query = query.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    count = query.scalar()
    return count if count is not None else 0

# Esta função parece ser para admin, não filtra por user_id
def count_all_fornecedores(db: Session, termo_busca: Optional[str] = None) -> int:
    query = db.query(func.count(models.Fornecedor.id))
    if termo_busca:
        query = query.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    count = query.scalar()
    return count if count is not None else 0
    
def update_fornecedor(db: Session, db_fornecedor: models.Fornecedor, fornecedor_update: schemas.FornecedorUpdate) -> models.Fornecedor:
    update_data = fornecedor_update.model_dump(exclude_unset=True)

    # Trata URLs que podem vir como None
    if "site_url" in update_data:
        site_url_val = update_data.pop("site_url")
        setattr(db_fornecedor, "site_url", str(site_url_val) if site_url_val is not None else None)
        
    if "link_busca_padrao" in update_data:
        link_busca_val = update_data.pop("link_busca_padrao")
        setattr(db_fornecedor, "link_busca_padrao", str(link_busca_val) if link_busca_val is not None else None)

    for key, value in update_data.items():
        setattr(db_fornecedor, key, value)
    
    if db.is_modified(db_fornecedor) and hasattr(db_fornecedor, 'updated_at'): 
        db_fornecedor.updated_at = datetime.now(timezone.utc) 
        
    try:
        db.commit()
        db.refresh(db_fornecedor)
    except SQLAlchemyError as e_sql_commit:
        db.rollback()
        print(f"ERRO CRUD SQL update_fornecedor ID {db_fornecedor.id}: {e_sql_commit}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar fornecedor.")
    return db_fornecedor

def delete_fornecedor(db: Session, db_fornecedor: models.Fornecedor) -> models.Fornecedor:
    # Verifica se há produtos associados
    if db_fornecedor.produtos: # Assumindo que 'produtos' é o nome do relationship em Fornecedor
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Não é possível deletar o fornecedor. Existem produtos associados a ele. Remova ou desassocie os produtos primeiro."
        )
    db.delete(db_fornecedor)
    db.commit()
    return db_fornecedor

# --- Produto CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate, user_id: int) -> models.Produto:
    produto_data_dict = produto.model_dump(exclude_unset=True)
    
    # Garante que dados_brutos seja um dict, mesmo que venha como None
    if "dados_brutos" not in produto_data_dict or produto_data_dict["dados_brutos"] is None:
        produto_data_dict["dados_brutos"] = {}
    
    # Garante que nome_chat_api tenha um valor (fallback para nome_base se não fornecido)
    if "nome_chat_api" not in produto_data_dict or produto_data_dict["nome_chat_api"] is None:
        produto_data_dict["nome_chat_api"] = produto_data_dict.get("nome_base")

    db_produto = models.Produto(**produto_data_dict, user_id=user_id)
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto

def get_produto(db: Session, produto_id: int, user_id: Optional[int] = None) -> Optional[models.Produto]:
    query = db.query(models.Produto).filter(models.Produto.id == produto_id)
    if user_id is not None: # Para verificar se o produto pertence ao usuário (usado nas rotas)
        query = query.filter(models.Produto.user_id == user_id)
    return query.first()

def get_produtos_by_user( 
    db: Session,
    user_id: Optional[int], 
    skip: int = 0,
    limit: int = 100, 
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc", # Default to "asc" for consistency
    search: Optional[str] = None, 
    fornecedor_id: Optional[int] = None,
    categoria: Optional[str] = None, 
    status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum] = None,
    status_titulo_ia: Optional[models.StatusGeracaoIAEnum] = None,
    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = None,
    product_type_id: Optional[int] = None,
    is_admin: bool = False 
) -> List[models.Produto]:
    
    query = db.query(models.Produto)

    if not is_admin and user_id is not None: 
        query = query.filter(models.Produto.user_id == user_id)
    elif not is_admin and user_id is None: 
        # Se não for admin e user_id for None, não deve retornar nada (ou levantar erro)
        # Isso protege contra o caso de um usuário não-admin tentar listar todos os produtos
        # A lógica na rota deve garantir que user_id seja passado para não-admins.
        return []

    if search: 
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(models.Produto.nome_base).like(search_term),
                func.lower(models.Produto.nome_chat_api).like(search_term),
                func.lower(models.Produto.descricao_original).like(search_term), # Assumindo que existe
                func.lower(models.Produto.descricao_chat_api).like(search_term), # Assumindo que existe
                func.lower(models.Produto.sku).like(search_term),
                func.lower(models.Produto.ean).like(search_term),
                func.lower(models.Produto.ncm).like(search_term),
                func.lower(models.Produto.marca).like(search_term), # Assumindo que existe
                func.lower(models.Produto.categoria_original).like(search_term), # Assumindo que existe
            )
        )
    if fornecedor_id is not None:
        query = query.filter(models.Produto.fornecedor_id == fornecedor_id)
    if categoria: 
        query = query.filter(func.lower(models.Produto.categoria_original).like(f"%{categoria.lower()}%"))

    if status_enriquecimento_web:
        query = query.filter(models.Produto.status_enriquecimento_web == status_enriquecimento_web)
    if status_titulo_ia:
        query = query.filter(models.Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(models.Produto.status_descricao_ia == status_descricao_ia)
    if product_type_id is not None:
        query = query.filter(models.Produto.product_type_id == product_type_id)

    if sort_by and hasattr(models.Produto, sort_by):
        column_to_sort = getattr(models.Produto, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(column_to_sort))
        else:
            query = query.order_by(asc(column_to_sort))
    else: # Default sort order
        query = query.order_by(models.Produto.id.desc()) 

    return query.offset(skip).limit(limit).all()


def count_produtos_by_user( 
    db: Session,
    user_id: Optional[int], 
    search: Optional[str] = None, 
    fornecedor_id: Optional[int] = None,
    categoria: Optional[str] = None,
    status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum] = None,
    status_titulo_ia: Optional[models.StatusGeracaoIAEnum] = None,
    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = None,
    product_type_id: Optional[int] = None,
    is_admin: bool = False
) -> int:
    query = db.query(func.count(models.Produto.id))

    if not is_admin and user_id is not None:
        query = query.filter(models.Produto.user_id == user_id)
    elif not is_admin and user_id is None:
        return 0

    if search: 
        search_term = f"%{search.lower()}%"
        query = query.filter(
             or_(
                func.lower(models.Produto.nome_base).like(search_term),
                func.lower(models.Produto.nome_chat_api).like(search_term),
                func.lower(models.Produto.descricao_original).like(search_term),
                func.lower(models.Produto.descricao_chat_api).like(search_term),
                func.lower(models.Produto.sku).like(search_term),
                func.lower(models.Produto.ean).like(search_term),
                func.lower(models.Produto.ncm).like(search_term),
                func.lower(models.Produto.marca).like(search_term),
                func.lower(models.Produto.categoria_original).like(search_term),
            )
        )
    if fornecedor_id is not None:
        query = query.filter(models.Produto.fornecedor_id == fornecedor_id)
    if categoria:
        query = query.filter(func.lower(models.Produto.categoria_original).like(f"%{categoria.lower()}%"))
        
    if status_enriquecimento_web:
        query = query.filter(models.Produto.status_enriquecimento_web == status_enriquecimento_web)
    if status_titulo_ia:
        query = query.filter(models.Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(models.Produto.status_descricao_ia == status_descricao_ia)
    if product_type_id is not None:
        query = query.filter(models.Produto.product_type_id == product_type_id)
        
    count = query.scalar()
    return count if count is not None else 0


def update_produto(db: Session, db_produto: models.Produto, produto_update: schemas.ProdutoUpdate) -> models.Produto:
    update_data = produto_update.model_dump(exclude_unset=True)
    
    # Tratamento especial para dados_brutos se for um dict para merge
    if "dados_brutos" in update_data and update_data["dados_brutos"] is not None:
        current_dados_brutos = db_produto.dados_brutos.copy() if isinstance(db_produto.dados_brutos, dict) else {}
        
        update_dados_brutos_val = update_data["dados_brutos"]
        update_dados_brutos_dict = {}
        if isinstance(update_dados_brutos_val, str): # Tenta carregar JSON se for string
            try: 
                import json # Import local para evitar no topo se não usado sempre
                update_dados_brutos_dict = json.loads(update_dados_brutos_val)
            except json.JSONDecodeError:
                print(f"AVISO CRUD: dados_brutos string em update_produto não é JSON válido: {update_dados_brutos_val}")
                # Decide se levanta erro ou ignora esta parte da atualização
        elif isinstance(update_dados_brutos_val, dict):
            update_dados_brutos_dict = update_dados_brutos_val
            
        if isinstance(update_dados_brutos_dict, dict): # Garante que é um dict após a tentativa de parse
            for k, v in update_dados_brutos_dict.items():
                if v is None and k in current_dados_brutos: # Remove a chave se o valor for None
                    del current_dados_brutos[k]
                elif v is not None: # Adiciona/atualiza se o valor não for None
                    current_dados_brutos[k] = v
        setattr(db_produto, "dados_brutos", current_dados_brutos)
        if "dados_brutos" in update_data: del update_data["dados_brutos"] # Remove para não processar no loop abaixo

    for key, value in update_data.items():
        # Converte strings de Enum para o tipo Enum real, se necessário
        if key == "status_enriquecimento_web" and value is not None and isinstance(value, str):
            try: setattr(db_produto, key, models.StatusEnriquecimentoEnum(value))
            except ValueError: print(f"AVISO CRUD: Valor inválido '{value}' para StatusEnriquecimentoEnum")
        elif key == "status_titulo_ia" and value is not None and isinstance(value, str):
            try: setattr(db_produto, key, models.StatusGeracaoIAEnum(value))
            except ValueError: print(f"AVISO CRUD: Valor inválido '{value}' para StatusGeracaoIAEnum (título)")
        elif key == "status_descricao_ia" and value is not None and isinstance(value, str):
            try: setattr(db_produto, key, models.StatusGeracaoIAEnum(value))
            except ValueError: print(f"AVISO CRUD: Valor inválido '{value}' para StatusGeracaoIAEnum (descrição)")
        else:
            setattr(db_produto, key, value)
            
    if db.is_modified(db_produto) and hasattr(db_produto, 'data_atualizacao'):
        db_produto.data_atualizacao = datetime.now(timezone.utc)
        
    try:
        db.commit()
        db.refresh(db_produto)
    except SQLAlchemyError as e_sql_commit:
        db.rollback()
        print(f"ERRO CRUD SQL ao commitar atualização do produto ID {db_produto.id if db_produto else 'desconhecido'}: {e_sql_commit}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar produto.")
    return db_produto

def delete_produto(db: Session, db_produto: models.Produto) -> models.Produto:
    db.delete(db_produto)
    db.commit()
    return db_produto

async def save_produto_image(db: Session, produto_id: int, file: UploadFile) -> str:
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    
    file_extension = ""
    original_filename = "unknown_image"
    if file.filename:
        original_filename = Path(file.filename).name # Pega apenas o nome do arquivo
        file_extension = Path(original_filename).suffix.lower().lstrip('.') # Pega a extensão sem o ponto

    if file_extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Formato de arquivo não permitido '{file_extension}'. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Cria um nome de arquivo seguro e único
    safe_original_name = "".join(c if c.isalnum() or c in ['.', '_', '-'] else '_' for c in original_filename)
    unique_prefix = secrets.token_hex(8)
    safe_filename = f"{unique_prefix}_{safe_original_name}"
    
    file_path = UPLOAD_DIRECTORY / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # Em produção, logar o erro 'e' de forma mais detalhada
        raise IOError(f"Não foi possível salvar o arquivo de imagem: {str(e)}")
    finally:
        await file.close() 
        
    # O caminho salvo no DB deve ser relativo à pasta que é servida estaticamente.
    # Se UPLOAD_DIRECTORY é "static/uploads" e "/static" serve a pasta "static",
    # então o caminho no DB deve ser "uploads/safe_filename"
    subfolder_name = UPLOAD_DIRECTORY.name # Ex: "uploads"
    relative_db_path = f"{subfolder_name}/{safe_filename}"
    return relative_db_path

# --- ProductType CRUD ---
def create_product_type(db: Session, product_type_data: schemas.ProductTypeCreate, user_id: Optional[int] = None) -> models.ProductType: 
    db_product_type = models.ProductType(**product_type_data.model_dump(), user_id=user_id) 
    db.add(db_product_type) 
    db.commit() 
    db.refresh(db_product_type) 
    return db_product_type 

# --- FUNÇÃO MODIFICADA COM LOGS ---
def get_product_type(db: Session, product_type_id: int) -> Optional[models.ProductType]: 
    # DEBUG LOG: Início da função get_product_type
    print(f"DEBUG LOG - CRUD (get_product_type): Buscando tipo de produto por ID: {product_type_id}")
    
    result = db.query(models.ProductType).options(
        selectinload(models.ProductType.attribute_templates) # Carrega os atributos junto
    ).filter(models.ProductType.id == product_type_id).first()
    
    if result:
        # DEBUG LOG: Tipo de produto encontrado
        print(f"DEBUG LOG - CRUD (get_product_type): Tipo de produto ENCONTRADO: ID={result.id}, Nome='{result.friendly_name}', UserID={result.user_id}")
        if result.attribute_templates:
            print(f"DEBUG LOG - CRUD (get_product_type): Atributos carregados: {len(result.attribute_templates)}")
        else:
            print(f"DEBUG LOG - CRUD (get_product_type): Nenhum atributo template associado.")
    else:
        # DEBUG LOG: Tipo de produto não encontrado
        print(f"DEBUG LOG - CRUD (get_product_type): Tipo de produto NÃO ENCONTRADO para ID: {product_type_id}")
        
    return result
# --- FIM DA FUNÇÃO MODIFICADA COM LOGS ---

def get_product_type_by_key_name(db: Session, key_name: str, user_id: Optional[int] = None) -> Optional[models.ProductType]: 
    # DEBUG LOG: Início da função get_product_type_by_key_name
    print(f"DEBUG LOG - CRUD (get_product_type_by_key_name): Buscando tipo de produto por KeyName: '{key_name}', UserID: {user_id}")
    query = db.query(models.ProductType).options(selectinload(models.ProductType.attribute_templates))
    
    # Filtra por key_name (case-insensitive)
    query = query.filter(func.lower(models.ProductType.key_name) == func.lower(key_name))
    
    # Filtra por user_id (se global, user_id é None; se específico, corresponde ao user_id)
    # Esta lógica permite que um usuário acesse tipos globais ou os seus próprios com o mesmo key_name
    # Se a intenção é key_name ser único globalmente ou único por usuário + globais, a query pode precisar de ajuste
    if user_id is not None:
        # Prioriza tipo do usuário, depois global se não achar do usuário
        user_specific_type = query.filter(models.ProductType.user_id == user_id).first()
        if user_specific_type:
            print(f"DEBUG LOG - CRUD: Tipo específico do usuário encontrado para key_name '{key_name}'")
            return user_specific_type
        # Se não achou específico do usuário, busca global
        global_type = query.filter(models.ProductType.user_id == None).first()
        if global_type:
            print(f"DEBUG LOG - CRUD: Tipo global encontrado para key_name '{key_name}' (após não achar específico do usuário).")
        else:
            print(f"DEBUG LOG - CRUD: Nenhum tipo (nem específico, nem global) encontrado para key_name '{key_name}'.")
        return global_type
    else: # Se user_id não foi fornecido, busca apenas tipos globais
        result = query.filter(models.ProductType.user_id == None).first()
        if result:
            print(f"DEBUG LOG - CRUD: Tipo global encontrado para key_name '{key_name}' (user_id não fornecido).")
        else:
            print(f"DEBUG LOG - CRUD: Nenhum tipo global encontrado para key_name '{key_name}' (user_id não fornecido).")
        return result


def get_product_types(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None) -> List[models.ProductType]: 
    query = db.query(models.ProductType).options(selectinload(models.ProductType.attribute_templates)) 
    if user_id: # Se user_id é fornecido, mostra tipos globais E os do usuário
        query = query.filter(or_(models.ProductType.user_id == user_id, models.ProductType.user_id == None)) 
    else: # Se user_id não é fornecido (ex: admin listando todos), não filtra por usuário (ou filtra apenas globais)
          # Para listar TODOS os tipos para um admin, não aplicar filtro de user_id aqui,
          # ou ter um parâmetro 'is_admin' como em get_produtos.
          # Por agora, se user_id is None, lista todos. A rota controlará a permissão.
          pass
    return query.order_by(models.ProductType.friendly_name).offset(skip).limit(limit).all() 

def update_product_type(db: Session, product_type_id: int, product_type_data: schemas.ProductTypeUpdate, user_id: Optional[int] = None) -> Optional[models.ProductType]: 
    db_product_type = get_product_type(db, product_type_id) 
    if not db_product_type: return None 

    # Checagem de permissão: ou é superuser, ou é dono do tipo (se não for global)
    if not settings.ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES and db_product_type.user_id is None and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuários não podem editar tipos de produto globais.")
    if db_product_type.user_id is not None and db_product_type.user_id != user_id and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a editar este tipo de produto.")

    update_data = product_type_data.model_dump(exclude_unset=True) 
    for key, value in update_data.items(): setattr(db_product_type, key, value) 
    
    if db.is_modified(db_product_type) and hasattr(db_product_type, 'updated_at'):
        db_product_type.updated_at = datetime.now(timezone.utc)

    db.commit() 
    db.refresh(db_product_type) 
    return db_product_type 

def delete_product_type(db: Session, product_type_id: int, user_id: Optional[int] = None) -> Optional[models.ProductType]: 
    db_product_type = get_product_type(db, product_type_id) 
    if not db_product_type: return None 

    # Checagem de permissão
    if not settings.ALLOW_USERS_TO_DELETE_GLOBAL_PRODUCT_TYPES and db_product_type.user_id is None and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuários não podem deletar tipos de produto globais.")
    if db_product_type.user_id is not None and db_product_type.user_id != user_id and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a deletar este tipo de produto.")

    produtos_associados_count = db.query(func.count(models.Produto.id)).filter(models.Produto.product_type_id == product_type_id).scalar()
    if produtos_associados_count > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tipo de produto em uso por {produtos_associados_count} produto(s), não pode ser deletado.")
    
    # Deletar atributos associados primeiro
    db.query(models.AttributeTemplate).filter(models.AttributeTemplate.product_type_id == product_type_id).delete(synchronize_session=False)
    
    db.delete(db_product_type) 
    db.commit() 
    return db_product_type 

# --- AttributeTemplate CRUD ---
def create_attribute_template(db: Session, attribute_template_data: schemas.AttributeTemplateCreate, product_type_id: int, user_id: Optional[int]=None) -> models.AttributeTemplate: 
    product_type = get_product_type(db, product_type_id) 
    if not product_type: 
        raise HTTPException(status_code=404, detail=f"ProductType com ID {product_type_id} não encontrado.") 
    
    # Checagem de permissão para adicionar atributo a um tipo
    if not settings.ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES and product_type.user_id is None and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a adicionar atributos a tipos de produto globais.")
    if product_type.user_id is not None and product_type.user_id != user_id and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a adicionar atributos a este tipo de produto.")
        
    db_attribute_template = models.AttributeTemplate( 
        **attribute_template_data.model_dump(),  
        product_type_id=product_type_id 
    )
    db.add(db_attribute_template) 
    db.commit() 
    db.refresh(db_attribute_template) 
    return db_attribute_template 

def get_attribute_template(db: Session, attribute_template_id: int) -> Optional[models.AttributeTemplate]: 
    return db.query(models.AttributeTemplate).filter(models.AttributeTemplate.id == attribute_template_id).first() 

def get_attribute_templates_by_product_type(db: Session, product_type_id: int) -> List[models.AttributeTemplate]: 
    return db.query(models.AttributeTemplate).filter(models.AttributeTemplate.product_type_id == product_type_id).order_by(models.AttributeTemplate.display_order, models.AttributeTemplate.id).all() 

def update_attribute_template(db: Session, attribute_template_id: int, attribute_template_data: schemas.AttributeTemplateUpdate, user_id: Optional[int]=None) -> Optional[models.AttributeTemplate]: 
    db_attribute_template = get_attribute_template(db, attribute_template_id) 
    if not db_attribute_template: return None 

    # Checagem de permissão para editar atributo (baseado no tipo de produto pai)
    product_type = db_attribute_template.product_type
    if not settings.ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES and product_type.user_id is None and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a editar atributos de tipos de produto globais.")
    if product_type.user_id is not None and product_type.user_id != user_id and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a editar atributos deste tipo de produto.")

    update_data = attribute_template_data.model_dump(exclude_unset=True) 
    for key, value in update_data.items(): setattr(db_attribute_template, key, value) 
    
    if db.is_modified(db_attribute_template) and hasattr(db_attribute_template, 'updated_at'):
        db_attribute_template.updated_at = datetime.now(timezone.utc)

    db.commit() 
    db.refresh(db_attribute_template) 
    return db_attribute_template 

def delete_attribute_template(db: Session, attribute_template_id: int, user_id: Optional[int]=None) -> Optional[models.AttributeTemplate]: 
    db_attribute_template = get_attribute_template(db, attribute_template_id) 
    if not db_attribute_template: return None 

    # Checagem de permissão para deletar atributo (baseado no tipo de produto pai)
    product_type = db_attribute_template.product_type
    if not settings.ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES and product_type.user_id is None and (not user_id or not get_user(db, user_id).is_superuser): # Assumindo que deletar é uma forma de edição
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a deletar atributos de tipos de produto globais.")
    if product_type.user_id is not None and product_type.user_id != user_id and (not user_id or not get_user(db, user_id).is_superuser):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a deletar atributos deste tipo de produto.")

    db.delete(db_attribute_template) 
    db.commit() 
    return db_attribute_template 

# --- RegistroUsoIA CRUD ---
def create_registro_uso_ia(db: Session, uso_ia: schemas.RegistroUsoIACreate, user_id: int) -> models.RegistroUsoIA:
    db_registro_uso_ia = models.RegistroUsoIA(
        **uso_ia.model_dump(exclude={'user_id'}), # Exclui user_id do dump se já está no schema
        user_id=user_id,
        timestamp=datetime.now(timezone.utc) # Garante que o timestamp é UTC e definido na criação
    )
    db.add(db_registro_uso_ia)
    db.commit()
    db.refresh(db_registro_uso_ia)
    return db_registro_uso_ia

def get_registros_uso_ia_by_user( 
    db: Session, user_id: int, skip: int = 0, limit: int = 100,
    tipo_acao: Optional[models.TipoAcaoIAEnum] = None, # Mudado para enum
    data_inicio: Optional[datetime] = None, 
    data_fim: Optional[datetime] = None 
) -> List[models.RegistroUsoIA]: 
    query = db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.user_id == user_id) 
    if tipo_acao: query = query.filter(models.RegistroUsoIA.tipo_acao == tipo_acao) 
    if data_inicio: query = query.filter(models.RegistroUsoIA.timestamp >= data_inicio) 
    if data_fim: 
        # Para incluir o dia inteiro de data_fim, ajustar para o início do próximo dia
        data_fim_ajustada = data_fim.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.filter(models.RegistroUsoIA.timestamp <= data_fim_ajustada) 
    return query.order_by(models.RegistroUsoIA.timestamp.desc()).offset(skip).limit(limit).all() 

def count_registros_uso_ia_by_user( 
    db: Session, user_id: int, 
    tipo_acao: Optional[models.TipoAcaoIAEnum] = None, # Mudado para enum
    data_inicio: Optional[datetime] = None, 
    data_fim: Optional[datetime] = None 
) -> int: 
    query = db.query(func.count(models.RegistroUsoIA.id)).filter(models.RegistroUsoIA.user_id == user_id) 
    if tipo_acao: query = query.filter(models.RegistroUsoIA.tipo_acao == tipo_acao) 
    if data_inicio: query = query.filter(models.RegistroUsoIA.timestamp >= data_inicio) 
    if data_fim: 
        data_fim_ajustada = data_fim.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.filter(models.RegistroUsoIA.timestamp <= data_fim_ajustada) 
    count = query.scalar() 
    return count if count is not None else 0 

def get_usos_ia_by_produto(db: Session, produto_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[models.RegistroUsoIA]: 
    prod = get_produto(db, produto_id=produto_id, user_id=user_id) 
    if not prod: return [] # Se o produto não existe ou não pertence ao usuário, retorna lista vazia
    return db.query(models.RegistroUsoIA).filter(
        models.RegistroUsoIA.produto_id == produto_id, 
        models.RegistroUsoIA.user_id == user_id # Redundante se get_produto já filtrou por user_id, mas seguro
    ).order_by(models.RegistroUsoIA.timestamp.desc()).offset(skip).limit(limit).all() 

def get_total_uso_ia_mes_corrente_por_tipo_acao(db: Session, user_id: int, tipo_acao: models.TipoAcaoIAEnum) -> int: 
    now = datetime.now(timezone.utc) 
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) 
    # Fim do mês é o início do próximo mês
    if start_of_month.month == 12:
        end_of_month_exclusive = start_of_month.replace(year=start_of_month.year + 1, month=1, day=1)
    else:
        end_of_month_exclusive = start_of_month.replace(month=start_of_month.month + 1, day=1)

    count = db.query(func.count(models.RegistroUsoIA.id)).filter( 
        models.RegistroUsoIA.user_id == user_id, 
        models.RegistroUsoIA.tipo_acao == tipo_acao, 
        models.RegistroUsoIA.timestamp >= start_of_month,
        models.RegistroUsoIA.timestamp < end_of_month_exclusive # Exclusivo do fim do mês
    ).scalar() 
    return count if count is not None else 0