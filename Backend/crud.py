# tdai_project/Backend/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Union
from datetime import datetime, timezone
import enum
from pydantic import HttpUrl

import models
import schemas
from core.config import pwd_context

# --- User CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate, plano_id: Optional[int] = None, role_id: Optional[int] = None) -> models.User:
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        nome=user.nome,
        idioma_preferido=user.idioma_preferido,
        is_active=True,
        is_superuser=False,
        plano_id=plano_id,
        role_id=role_id,
        chave_openai_pessoal=user.chave_openai_pessoal
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: Union[schemas.UserUpdate, schemas.UserUpdateByAdmin]) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        hashed_password = pwd_context.hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"]
    for key, value in update_data.items():
        setattr(db_user, key, value)
    if db.is_modified(db_user):
        db_user.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(db_user)
    except SQLAlchemyError as e_sql_commit:
        db.rollback()
        print(f"ERRO CRUD SQL ao commitar atualização do usuário ID {db_user.id}: {e_sql_commit}")
        raise
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user: return None
    db.delete(db_user)
    db.commit()
    return db_user

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
def get_plano_by_name(db: Session, name: str) -> Optional[models.Plano]:
    return db.query(models.Plano).filter(models.Plano.name == name).first()
def get_plano(db: Session, plano_id: int) -> Optional[models.Plano]:
    return db.query(models.Plano).filter(models.Plano.id == plano_id).first()
def get_planos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Plano]:
    return db.query(models.Plano).order_by(models.Plano.name).offset(skip).limit(limit).all()
def create_plano(db: Session, plano: schemas.PlanoCreate) -> models.Plano:
    db_plano = models.Plano(**plano.model_dump())
    db.add(db_plano)
    db.commit()
    db.refresh(db_plano)
    return db_plano

# --- Fornecedor CRUD ---
def create_fornecedor(db: Session, fornecedor: schemas.FornecedorCreate, user_id: int) -> models.Fornecedor:
    fornecedor_data = fornecedor.model_dump()
    if fornecedor_data.get("site_url") is not None:
        fornecedor_data["site_url"] = str(fornecedor_data["site_url"])
    if fornecedor_data.get("link_busca_padrao") is not None:
        fornecedor_data["link_busca_padrao"] = str(fornecedor_data["link_busca_padrao"])
    db_fornecedor = models.Fornecedor(**fornecedor_data, user_id=user_id)
    db.add(db_fornecedor); db.commit(); db.refresh(db_fornecedor)
    return db_fornecedor

def get_fornecedor(db: Session, fornecedor_id: int, user_id: Optional[int] = None) -> Optional[models.Fornecedor]:
    q = db.query(models.Fornecedor).filter(models.Fornecedor.id == fornecedor_id)
    if user_id: q = q.filter(models.Fornecedor.user_id == user_id)
    return q.first()

def get_fornecedores_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100, termo_busca: Optional[str] = None) -> List[models.Fornecedor]:
    q = db.query(models.Fornecedor).filter(models.Fornecedor.user_id == user_id)
    if termo_busca: q = q.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    return q.order_by(models.Fornecedor.nome).offset(skip).limit(limit).all()

def count_fornecedores_by_user(db: Session, user_id: int, termo_busca: Optional[str] = None) -> int:
    q = db.query(func.count(models.Fornecedor.id)).filter(models.Fornecedor.user_id == user_id)
    if termo_busca: q = q.filter(models.Fornecedor.nome.ilike(f"%{termo_busca}%"))
    return q.scalar() or 0

def update_fornecedor(db: Session, db_fornecedor: models.Fornecedor, fornecedor_update: schemas.FornecedorUpdate) -> models.Fornecedor:
    update_data = fornecedor_update.model_dump(exclude_unset=True)
    if "site_url" in update_data:
        setattr(db_fornecedor, "site_url", str(update_data.pop("site_url", db_fornecedor.site_url)))
    if "link_busca_padrao" in update_data:
        setattr(db_fornecedor, "link_busca_padrao", str(update_data.pop("link_busca_padrao", db_fornecedor.link_busca_padrao)))
    for key, value in update_data.items(): setattr(db_fornecedor, key, value)
    if db.is_modified(db_fornecedor): db_fornecedor.updated_at = datetime.now(timezone.utc)
    try:
        db.commit(); db.refresh(db_fornecedor)
    except SQLAlchemyError as e: db.rollback(); print(f"ERRO CRUD SQL update_fornecedor ID {db_fornecedor.id}: {e}"); raise
    return db_fornecedor

def delete_fornecedor(db: Session, db_fornecedor: models.Fornecedor) -> models.Fornecedor:
    db.delete(db_fornecedor); db.commit()
    return db_fornecedor

# --- Produto CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate, user_id: int) -> models.Produto:
    produto_data_dict = produto.model_dump(exclude_unset=True)
    if produto_data_dict.get("dados_brutos") is None: 
        produto_data_dict["dados_brutos"] = {}
    
    # O default do modelo models.Produto (StatusEnriquecimentoEnum.PENDENTE) será usado
    # ao criar o objeto models.Produto se status_enriquecimento_web não estiver em produto_data_dict.
    # O SQLAlchemy usará o .value (agora MAIÚSCULO) desse default.
    
    db_produto = models.Produto(**produto_data_dict, user_id=user_id)
    db.add(db_produto); db.commit(); db.refresh(db_produto)
    return db_produto

def get_produto(db: Session, produto_id: int, user_id: Optional[int] = None) -> Optional[models.Produto]:
    q = db.query(models.Produto).filter(models.Produto.id == produto_id)
    if user_id: q = q.filter(models.Produto.user_id == user_id)
    return q.first()

def get_produtos_by_user(
    db: Session, user_id: int, skip: int = 0, limit: int = 100,
    fornecedor_id: Optional[int] = None,
    status_enriquecimento: Optional[Union[models.StatusEnriquecimentoEnum, str]] = None,
    termo_busca: Optional[str] = None
) -> List[models.Produto]:
    q = db.query(models.Produto).filter(models.Produto.user_id == user_id)
    if fornecedor_id is not None: q = q.filter(models.Produto.fornecedor_id == fornecedor_id)
    
    if status_enriquecimento is not None:
        status_valor_comparar: Optional[str] = None
        if isinstance(status_enriquecimento, models.StatusEnriquecimentoEnum):
            status_valor_comparar = status_enriquecimento.value # Será MAIÚSCULO
        elif isinstance(status_enriquecimento, str):
            # Tenta converter para o valor do enum, assumindo que a string pode ser um nome ou valor
            try:
                status_valor_comparar = models.StatusEnriquecimentoEnum(status_enriquecimento.lower()).value # Tenta com minúsculo primeiro (se input for "pendente")
            except ValueError:
                try:
                    status_valor_comparar = models.StatusEnriquecimentoEnum[status_enriquecimento.upper()].value # Tenta com nome maiúsculo (se input for "PENDENTE")
                except KeyError:
                    status_valor_comparar = None 
        
        if status_valor_comparar: # Compara com o .value (MAIÚSCULO)
            q = q.filter(models.Produto.status_enriquecimento_web == status_valor_comparar)

    if termo_busca:
        q = q.filter( (models.Produto.nome_base.ilike(f"%{termo_busca}%")) | (models.Produto.marca.ilike(f"%{termo_busca}%")) | (models.Produto.categoria_original.ilike(f"%{termo_busca}%")) )
    return q.order_by(models.Produto.id.desc()).offset(skip).limit(limit).all()

def count_produtos_by_user(
    db: Session, user_id: int, fornecedor_id: Optional[int] = None,
    status_enriquecimento: Optional[Union[models.StatusEnriquecimentoEnum, str]] = None,
    termo_busca: Optional[str] = None
) -> int:
    q = db.query(func.count(models.Produto.id)).filter(models.Produto.user_id == user_id)
    if fornecedor_id is not None: q = q.filter(models.Produto.fornecedor_id == fornecedor_id)

    if status_enriquecimento is not None:
        status_valor_comparar: Optional[str] = None
        if isinstance(status_enriquecimento, models.StatusEnriquecimentoEnum):
            status_valor_comparar = status_enriquecimento.value # MAIÚSCULO
        elif isinstance(status_enriquecimento, str):
            try:
                status_valor_comparar = models.StatusEnriquecimentoEnum(status_enriquecimento.lower()).value
            except ValueError:
                try:
                    status_valor_comparar = models.StatusEnriquecimentoEnum[status_enriquecimento.upper()].value
                except KeyError:
                    status_valor_comparar = None
        if status_valor_comparar:
             q = q.filter(models.Produto.status_enriquecimento_web == status_valor_comparar)

    if termo_busca:
        q = q.filter( (models.Produto.nome_base.ilike(f"%{termo_busca}%")) | (models.Produto.marca.ilike(f"%{termo_busca}%")) | (models.Produto.categoria_original.ilike(f"%{termo_busca}%")) )
    return q.scalar() or 0

def update_produto(db: Session, db_produto: models.Produto, produto_update: schemas.ProdutoUpdate) -> models.Produto:
    update_data = produto_update.model_dump(exclude_unset=True)

    if "dados_brutos" in update_data and update_data["dados_brutos"] is not None:
        if db_produto.dados_brutos is None: db_produto.dados_brutos = {}
        current_dados_brutos = db_produto.dados_brutos.copy() if isinstance(db_produto.dados_brutos, dict) else {}
        for k, v in update_data["dados_brutos"].items():
            if v is None and k in current_dados_brutos: del current_dados_brutos[k]
            elif v is not None: current_dados_brutos[k] = v
        setattr(db_produto, "dados_brutos", current_dados_brutos)
        del update_data["dados_brutos"]

    for key, value in update_data.items():
        if key == "status_enriquecimento_web" and value is not None:
            if isinstance(value, str):
                try:
                    # 'value' deve ser a string MAIÚSCULA, ex: "FALHA_CONFIGURACAO_API_EXTERNA"
                    # que corresponde ao .value do enum Python após a alteração em models.py
                    enum_member = models.StatusEnriquecimentoEnum(value)
                    setattr(db_produto, key, enum_member) # Atribui o objeto enum ao modelo SQLAlchemy
                except ValueError:
                    print(f"AVISO CRUD: String de status '{value}' inválida para StatusEnriquecimentoEnum. Status não alterado.")
            elif isinstance(value, models.StatusEnriquecimentoEnum): # Se por acaso um objeto enum for passado
                 setattr(db_produto, key, value)
            else:
                print(f"AVISO CRUD: Tipo inesperado '{type(value)}' para status_enriquecimento_web. Status não alterado.")
        else:
            setattr(db_produto, key, value)

    if db.is_modified(db_produto):
        db_produto.updated_at = datetime.now(timezone.utc)
    
    try:
        db.commit()
        db.refresh(db_produto)
    except SQLAlchemyError as e_sql_commit:
        db.rollback()
        print(f"ERRO CRUD SQL ao commitar atualização do produto ID {db_produto.id if db_produto else 'desconhecido'}: {e_sql_commit}")
        raise 
    
    return db_produto

def delete_produto(db: Session, db_produto: models.Produto) -> models.Produto:
    db.delete(db_produto); db.commit()
    return db_produto

# --- UsoIA CRUD ---
def create_uso_ia(db: Session, uso_ia: schemas.UsoIACreate, user_id: int) -> models.UsoIA:
    db_uso_ia = models.UsoIA(**uso_ia.model_dump(exclude={'user_id'}), user_id=user_id)
    db.add(db_uso_ia); db.commit(); db.refresh(db_uso_ia)
    return db_uso_ia

def get_usos_ia_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.UsoIA]:
    return db.query(models.UsoIA).filter(models.UsoIA.user_id == user_id).order_by(models.UsoIA.timestamp.desc()).offset(skip).limit(limit).all()

def count_usos_ia_by_user(db: Session, user_id: int) -> int:
    return db.query(func.count(models.UsoIA.id)).filter(models.UsoIA.user_id == user_id).scalar() or 0

def get_usos_ia_by_produto(db: Session, produto_id: int, user_id: int, skip: int = 0, limit: int = 100) -> List[models.UsoIA]:
    prod = get_produto(db, produto_id=produto_id, user_id=user_id)
    if not prod: return []
    return db.query(models.UsoIA).filter(models.UsoIA.produto_id == produto_id).order_by(models.UsoIA.timestamp.desc()).offset(skip).limit(limit).all()

def count_usos_ia_by_user_and_type_no_mes_corrente(db: Session, user_id: int, tipo_geracao_prefix: str) -> int:
    agora = datetime.now(timezone.utc)
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fim_mes_exclusivo = (inicio_mes.replace(month=inicio_mes.month % 12 + 1, day=1) if inicio_mes.month < 12 else inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1))
    
    return db.query(func.count(models.UsoIA.id)).filter(
        models.UsoIA.user_id == user_id,
        models.UsoIA.timestamp >= inicio_mes,
        models.UsoIA.timestamp < fim_mes_exclusivo,
        models.UsoIA.tipo_geracao.startswith(tipo_geracao_prefix)
    ).scalar() or 0