import logging
from typing import List, Optional, Union
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from Backend.core.config import settings
from Backend.core import security
from Backend.models import User, Role, Plano
from Backend import schemas

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
        is_active=True,
        is_superuser=False
    )

    if user.plano_id:
        plano = get_plano(db, plano_id=user.plano_id)
        if plano:
            db_user.plano_id = plano.id
            db_user.limite_produtos = plano.limite_produtos
            db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
            db_user.limite_geracao_ia = plano.limite_geracao_ia
        else:
            logger.warning(
                f"Plano com ID {user.plano_id} não encontrado ao criar usuário {user.email}. Usando defaults."
            )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, db_user: User, user_update: Union[schemas.UserUpdate, schemas.UserUpdateByAdmin, schemas.UserUpdateOAuth]) -> User:
    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        hashed_password = security.get_password_hash(update_data["password"])
        db_user.hashed_password = hashed_password
        del update_data["password"]

    if "plano_id" in update_data:
        new_plano_id = update_data["plano_id"]
        if new_plano_id is None:
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
            else:
                logger.warning(
                    f"Plano com ID {new_plano_id} não encontrado ao atualizar usuário {db_user.email}. Plano não alterado."
                )
        if "plano_id" in update_data:
            del update_data["plano_id"]

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
        idioma_preferido=user_oauth.idioma_preferido,
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

    default_role = get_role_by_name(db, "user")
    if default_role:
        db_user.role_id = default_role.id

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_provider(db: Session, provider: str, provider_user_id: str) -> Optional[User]:
    return db.query(User).filter(User.provider == provider, User.provider_user_id == provider_user_id).first()

def set_user_password_reset_token(db: Session, user: User, token_hash: str, expires_at: datetime) -> None:
    user.reset_password_token = token_hash
    user.reset_password_token_expires_at = expires_at
    db.commit()
    db.refresh(user)

def get_user_by_reset_token(db: Session, token_hash: str) -> Optional[User]:
    return db.query(User).filter(User.reset_password_token == token_hash).first()

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
