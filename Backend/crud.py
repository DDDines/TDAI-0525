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
from pydantic import HttpUrl 

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
# ... (Funções User, Role, Plano CRUD permanecem como na mensagem 004_R42) ...
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
        "is_superuser": False,
        "chave_openai_pessoal": user.chave_openai_pessoal,
        "chave_google_gemini_pessoal": user.chave_google_gemini_pessoal
    }
    if role_id:
        db_user_data["role_id"] = role_id

    db_user = models.User(**db_user_data)

    effective_plano_id = user.plano_id if hasattr(user, 'plano_id') and user.plano_id is not None else plano_id
    
    if effective_plano_id:
        plano = get_plano(db, plano_id=effective_plano_id)
        if not plano:
            raise HTTPException(status_code=404, detail=f"Plano com ID {effective_plano_id} não encontrado.")
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

def update_user(db: Session, user_id: int, user_update_data: Union[schemas.UserUpdate, schemas.UserUpdateByAdmin, schemas.UserUpdateOAuth]) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    update_data = user_update_data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"]
    if "email" in update_data and db_user.email: 
        update_data["email"] = update_data["email"].lower()
    if "plano_id" in update_data:
        plano_id = update_data.pop("plano_id") 
        if plano_id is None:
            db_user.plano_id = None
            db_user.plano = None
            db_user.limite_produtos = settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO 
            db_user.limite_enriquecimento_web = settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO
            db_user.limite_geracao_ia = settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO
            db_user.data_expiracao_plano = None
        else:
            plano = get_plano(db, plano_id=plano_id)
            if not plano:
                raise HTTPException(status_code=404, detail=f"Plano com ID {plano_id} não encontrado.")
            db_user.plano = plano 
            db_user.plano_id = plano.id 
            db_user.limite_produtos = plano.limite_produtos
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano.limite_geracao_ia
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar usuário: {e_sql_commit}")
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[models.User]:
    # ... (código como antes)
    db_user = get_user(db, user_id)
    if not db_user: return None
    db.delete(db_user)
    db.commit()
    return db_user

def create_user_oauth(db: Session, user_data: schemas.UserCreateOAuth, plano_id: Optional[int] = None) -> models.User:
    # ... (código como antes)
    db_user = models.User(
        email=user_data.email.lower(),
        nome_completo=user_data.nome_completo, 
        provider=user_data.provider, 
        provider_user_id=user_data.provider_user_id, 
        is_active=True,  
        is_superuser=False, 
        hashed_password=None 
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
    # ... (código como antes)
    db_user = get_user(db, user_id) 
    if db_user: 
        db_user.reset_password_token = token 
        db_user.reset_password_token_expires_at = expires_at 
        db.commit() 
        db.refresh(db_user) 
    return db_user 

def get_user_by_reset_token(db: Session, token: str) -> Optional[models.User]: 
    # ... (código como antes)
    return db.query(models.User).filter(models.User.reset_password_token == token).first() 

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
    # ... (código como antes)
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
    if fornecedor_data.get("site_url") is not None:
        fornecedor_data["site_url"] = str(fornecedor_data["site_url"])
    if fornecedor_data.get("link_busca_padrao") is not None:
        fornecedor_data["link_busca_padrao"] = str(fornecedor_data["link_busca_padrao"])
    db_fornecedor = models.Fornecedor(**fornecedor_data, user_id=user_id)
    db.add(db_fornecedor)
    try:
        db.commit()
        db.refresh(db_fornecedor)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar fornecedor no banco de dados.")
    return db_fornecedor

def get_fornecedor(db: Session, fornecedor_id: int, user_id: Optional[int] = None) -> Optional[models.Fornecedor]:
    # ... (código como antes)
    query = db.query(models.Fornecedor).filter(models.Fornecedor.id == fornecedor_id)
    if user_id is not None: 
        query = query.filter(models.Fornecedor.user_id == user_id)
    return query.first()

def get_fornecedores_by_user(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    termo_busca: Optional[str] = None
) -> List[models.Fornecedor]:
    # ... (código como antes)
    query = db.query(models.Fornecedor).filter(models.Fornecedor.user_id == user_id)
    if termo_busca:
        query = query.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    return query.order_by(models.Fornecedor.nome).offset(skip).limit(limit).all()

def count_fornecedores_by_user(db: Session, user_id: int, termo_busca: Optional[str] = None) -> int:
    # ... (código como antes)
    query = db.query(func.count(models.Fornecedor.id)).filter(models.Fornecedor.user_id == user_id)
    if termo_busca:
        query = query.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    count = query.scalar()
    return count if count is not None else 0

def count_all_fornecedores(db: Session, termo_busca: Optional[str] = None) -> int:
    # ... (código como antes)
    query = db.query(func.count(models.Fornecedor.id))
    if termo_busca:
        query = query.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    count = query.scalar()
    return count if count is not None else 0
    
def update_fornecedor(db: Session, db_fornecedor: models.Fornecedor, fornecedor_update: schemas.FornecedorUpdate) -> models.Fornecedor:
    # ... (código como antes)
    update_data = fornecedor_update.model_dump(exclude_unset=True)
    if "site_url" in update_data and update_data["site_url"] is not None:
        setattr(db_fornecedor, "site_url", str(update_data.pop("site_url")))
    elif "site_url" in update_data and update_data["site_url"] is None: 
         setattr(db_fornecedor, "site_url", None)
         if "site_url" in update_data: update_data.pop("site_url")
    if "link_busca_padrao" in update_data and update_data["link_busca_padrao"] is not None:
        setattr(db_fornecedor, "link_busca_padrao", str(update_data.pop("link_busca_padrao")))
    elif "link_busca_padrao" in update_data and update_data["link_busca_padrao"] is None:
        setattr(db_fornecedor, "link_busca_padrao", None)
        if "link_busca_padrao" in update_data: update_data.pop("link_busca_padrao")
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
    # ... (código como antes)
    if db_fornecedor.produtos: 
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Não é possível deletar o fornecedor. Existem produtos associados a ele. Remova ou desassocie os produtos primeiro."
        )
    db.delete(db_fornecedor)
    db.commit()
    return db_fornecedor

# --- Produto CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate, user_id: int) -> models.Produto:
    # ... (código como antes, garantindo que nome_base está no modelo Produto) ...
    produto_data_dict = produto.model_dump(exclude_unset=True)
    if "dados_brutos" not in produto_data_dict or produto_data_dict["dados_brutos"] is None:
        produto_data_dict["dados_brutos"] = {}
    if "nome_chat_api" not in produto_data_dict or produto_data_dict["nome_chat_api"] is None:
        produto_data_dict["nome_chat_api"] = produto_data_dict.get("nome_base")
    db_produto = models.Produto(**produto_data_dict, user_id=user_id)
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto

def get_produto(db: Session, produto_id: int, user_id: Optional[int] = None) -> Optional[models.Produto]:
    # ... (código como antes) ...
    query = db.query(models.Produto).filter(models.Produto.id == produto_id)
    if user_id is not None: 
        query = query.filter(models.Produto.user_id == user_id)
    return query.first()

# ATENÇÃO: CORREÇÃO PRINCIPAL PARA O TypeError APLICADA AQUI
def get_produtos_by_user( 
    db: Session,
    user_id: Optional[int], # Mantido Optional para compatibilidade com chamada de admin em routers/produtos.py
    skip: int = 0,
    limit: int = 100, 
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    search: Optional[str] = None, # <--- PARÂMETRO 'search' ADICIONADO
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
        return []

    if search: # <--- LÓGICA DE BUSCA USANDO O PARÂMETRO 'search'
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
                # Adicionar marca e categoria_original à busca se desejar
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

    if sort_by and hasattr(models.Produto, sort_by):
        column_to_sort = getattr(models.Produto, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(column_to_sort))
        else:
            query = query.order_by(asc(column_to_sort))
    else:
        query = query.order_by(models.Produto.id.desc()) 

    return query.offset(skip).limit(limit).all()


def count_produtos_by_user( 
    db: Session,
    user_id: Optional[int], 
    search: Optional[str] = None, # <--- PARÂMETRO 'search' ADICIONADO
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

    if search: # <--- LÓGICA DE BUSCA USANDO O PARÂMETRO 'search'
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
    # ... (código como antes, garantindo que os status IA são tratados) ...
    update_data = produto_update.model_dump(exclude_unset=True)
    if "dados_brutos" in update_data and update_data["dados_brutos"] is not None:
        current_dados_brutos = db_produto.dados_brutos.copy() if isinstance(db_produto.dados_brutos, dict) else {}
        update_dados_brutos_dict = update_data["dados_brutos"]
        if isinstance(update_dados_brutos_dict, str): # Tenta carregar JSON se for string
            try: 
                import json
                update_dados_brutos_dict = json.loads(update_dados_brutos_dict)
            except json.JSONDecodeError:
                print(f"AVISO CRUD: dados_brutos string não é JSON válido: {update_dados_brutos_dict}")
                update_dados_brutos_dict = {} # Ou levanta erro
        if isinstance(update_dados_brutos_dict, dict):
            for k, v in update_dados_brutos_dict.items():
                if v is None and k in current_dados_brutos: del current_dados_brutos[k]
                elif v is not None: current_dados_brutos[k] = v
        setattr(db_produto, "dados_brutos", current_dados_brutos)
        if "dados_brutos" in update_data: del update_data["dados_brutos"] # Evita processar novamente no loop abaixo
    for key, value in update_data.items():
        if key == "status_enriquecimento_web" and value is not None:
            setattr(db_produto, key, models.StatusEnriquecimentoEnum(value) if isinstance(value, str) else value)
        elif key == "status_titulo_ia" and value is not None:
            setattr(db_produto, key, models.StatusGeracaoIAEnum(value) if isinstance(value, str) else value)
        elif key == "status_descricao_ia" and value is not None:
            setattr(db_produto, key, models.StatusGeracaoIAEnum(value) if isinstance(value, str) else value)
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
    # ... (código como antes) ...
    db.delete(db_produto)
    db.commit()
    return db_produto

async def save_produto_image(db: Session, produto_id: int, file: UploadFile) -> str:
    # ... (código como antes) ...
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    file_extension = ""
    if file.filename:
        file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Formato de arquivo não permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}")
    safe_filename = f"{secrets.token_hex(8)}_{file.filename.replace(' ', '_') if file.filename else 'unknown_image'}"
    file_path = UPLOAD_DIRECTORY / safe_filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise IOError(f"Não foi possível salvar o arquivo de imagem: {e}")
    finally:
        await file.close() 
    subfolder_name = UPLOAD_DIRECTORY.name 
    relative_db_path = f"{subfolder_name}/{safe_filename}"
    return relative_db_path

# --- ProductType CRUD ---
# ... (código como antes) ...
def create_product_type(db: Session, product_type_data: schemas.ProductTypeCreate, user_id: Optional[int] = None) -> models.ProductType: 
    db_product_type = models.ProductType(**product_type_data.model_dump(), user_id=user_id) 
    db.add(db_product_type) 
    db.commit() 
    db.refresh(db_product_type) 
    return db_product_type 
def get_product_type(db: Session, product_type_id: int) -> Optional[models.ProductType]: 
    return db.query(models.ProductType).options(selectinload(models.ProductType.attribute_templates)).filter(models.ProductType.id == product_type_id).first() 
def get_product_type_by_key_name(db: Session, key_name: str) -> Optional[models.ProductType]: 
    return db.query(models.ProductType).options(selectinload(models.ProductType.attribute_templates)).filter(models.ProductType.key_name == key_name).first() 
def get_product_types(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None) -> List[models.ProductType]: 
    query = db.query(models.ProductType).options(selectinload(models.ProductType.attribute_templates)) 
    if user_id: 
        query = query.filter(or_(models.ProductType.user_id == user_id, models.ProductType.user_id == None)) 
    return query.order_by(models.ProductType.friendly_name).offset(skip).limit(limit).all() 
def update_product_type(db: Session, product_type_id: int, product_type_data: schemas.ProductTypeUpdate) -> Optional[models.ProductType]: 
    db_product_type = get_product_type(db, product_type_id) 
    if not db_product_type: return None 
    update_data = product_type_data.model_dump(exclude_unset=True) 
    for key, value in update_data.items(): setattr(db_product_type, key, value) 
    db.commit() 
    db.refresh(db_product_type) 
    return db_product_type 
def delete_product_type(db: Session, product_type_id: int) -> Optional[models.ProductType]: 
    db_product_type = get_product_type(db, product_type_id) 
    if not db_product_type: return None 
    # Adicionar verificação se o tipo de produto está em uso
    produtos_associados = db.query(models.Produto).filter(models.Produto.product_type_id == product_type_id).first()
    if produtos_associados:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tipo de produto em uso, não pode ser deletado.")
    db.delete(db_product_type) 
    db.commit() 
    return db_product_type 

# --- AttributeTemplate CRUD ---
# ... (código como antes) ...
def create_attribute_template(db: Session, attribute_template_data: schemas.AttributeTemplateCreate, product_type_id: int) -> models.AttributeTemplate: 
    product_type = get_product_type(db, product_type_id) 
    if not product_type: 
        raise HTTPException(status_code=404, detail=f"ProductType com ID {product_type_id} não encontrado.") 
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
    return db.query(models.AttributeTemplate).filter(models.AttributeTemplate.product_type_id == product_type_id).order_by(models.AttributeTemplate.display_order).all() 
def update_attribute_template(db: Session, attribute_template_id: int, attribute_template_data: schemas.AttributeTemplateUpdate) -> Optional[models.AttributeTemplate]: 
    db_attribute_template = get_attribute_template(db, attribute_template_id) 
    if not db_attribute_template: return None 
    update_data = attribute_template_data.model_dump(exclude_unset=True) 
    for key, value in update_data.items(): setattr(db_attribute_template, key, value) 
    db.commit() 
    db.refresh(db_attribute_template) 
    return db_attribute_template 
def delete_attribute_template(db: Session, attribute_template_id: int) -> Optional[models.AttributeTemplate]: 
    db_attribute_template = get_attribute_template(db, attribute_template_id) 
    if not db_attribute_template: return None 
    db.delete(db_attribute_template) 
    db.commit() 
    return db_attribute_template 

# --- RegistroUsoIA CRUD ---
# ... (código como na mensagem 004_R42, usando RegistroUsoIA e RegistroUsoIACreate) ...
def create_registro_uso_ia(db: Session, uso_ia: schemas.RegistroUsoIACreate, user_id: int) -> models.RegistroUsoIA:
    db_registro_uso_ia = models.RegistroUsoIA(
        **uso_ia.model_dump(exclude={'user_id'}), user_id=user_id # Adicionado exclude
    )
    db.add(db_registro_uso_ia)
    db.commit()
    db.refresh(db_registro_uso_ia)
    return db_registro_uso_ia
def get_registros_uso_ia_by_user( 
    db: Session, user_id: int, skip: int = 0, limit: int = 100,
    tipo_geracao: Optional[str] = None, 
    data_inicio: Optional[datetime] = None, 
    data_fim: Optional[datetime] = None 
) -> List[models.RegistroUsoIA]: 
    query = db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.user_id == user_id) 
    if tipo_geracao: query = query.filter(models.RegistroUsoIA.tipo_geracao.ilike(f"%{tipo_geracao}%")) 
    if data_inicio: query = query.filter(models.RegistroUsoIA.timestamp >= data_inicio) 
    if data_fim: query = query.filter(models.RegistroUsoIA.timestamp < (data_fim + timedelta(days=1))) 
    return query.order_by(models.RegistroUsoIA.timestamp.desc()).offset(skip).limit(limit).all() 
def count_registros_uso_ia_by_user( 
    db: Session, user_id: int, 
    tipo_geracao: Optional[str] = None, 
    data_inicio: Optional[datetime] = None, 
    data_fim: Optional[datetime] = None 
) -> int: 
    query = db.query(func.count(models.RegistroUsoIA.id)).filter(models.RegistroUsoIA.user_id == user_id) 
    if tipo_geracao: query = query.filter(models.RegistroUsoIA.tipo_geracao.ilike(f"%{tipo_geracao}%")) 
    if data_inicio: query = query.filter(models.RegistroUsoIA.timestamp >= data_inicio) 
    if data_fim: query = query.filter(models.RegistroUsoIA.timestamp < (data_fim + timedelta(days=1))) 
    count = query.scalar() 
    return count if count is not None else 0 
def get_usos_ia_by_produto(db: Session, produto_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[models.RegistroUsoIA]: 
    prod = get_produto(db, produto_id=produto_id, user_id=user_id) 
    if not prod: return []
    return db.query(models.RegistroUsoIA).filter(models.RegistroUsoIA.produto_id == produto_id, models.RegistroUsoIA.user_id == user_id).order_by(models.RegistroUsoIA.timestamp.desc()).offset(skip).limit(limit).all() 
def count_usos_ia_by_user_and_type_no_mes_corrente(db: Session, user_id: int, tipo_geracao_prefix: str) -> int: 
    agora = datetime.now(timezone.utc) 
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0) 
    if inicio_mes.month == 12:
        fim_mes_exclusivo = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1)
    else:
        fim_mes_exclusivo = inicio_mes.replace(month=inicio_mes.month + 1, day=1)
    count = db.query(func.count(models.RegistroUsoIA.id)).filter( 
        models.RegistroUsoIA.user_id == user_id, 
        models.RegistroUsoIA.timestamp >= inicio_mes, 
        models.RegistroUsoIA.timestamp < fim_mes_exclusivo, 
        models.RegistroUsoIA.tipo_geracao.startswith(tipo_geracao_prefix) 
    ).scalar() 
    return count if count is not None else 0
def get_total_uso_ia_mes_corrente_por_tipo(db: Session, user_id: int, tipo_geracao: str) -> int: 
    now = datetime.now(timezone.utc) 
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) 
    count = db.query(func.count(models.RegistroUsoIA.id)).filter( 
        models.RegistroUsoIA.user_id == user_id, 
        models.RegistroUsoIA.tipo_geracao == tipo_geracao, 
        models.RegistroUsoIA.timestamp >= start_of_month 
    ).scalar() 
    return count if count is not None else 0