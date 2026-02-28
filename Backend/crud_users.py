import logging
from datetime import datetime
from typing import List, Optional, Union

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.core import security
from Backend.core.config import settings
from Backend.models import Plano, Role, User

logger = logging.getLogger(__name__)


def _apply_default_plan_limits(db_user: User) -> None:
    db_user.limite_produtos = settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO
    db_user.limite_enriquecimento_web = settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO
    db_user.limite_geracao_ia = settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO


def _apply_plano_limits(db: Session, db_user: User, plano_id: Optional[int]) -> None:
    if plano_id is None:
        db_user.plano_id = None
        _apply_default_plan_limits(db_user)
        db_user.data_expiracao_plano = None
        return

    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        logger.warning(
            "Plano ID %s nao encontrado para usuario %s. Mantendo limites atuais.",
            plano_id,
            db_user.email,
        )
        return

    db_user.plano_id = plano.id
    db_user.limite_produtos = plano.limite_produtos
    db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
    db_user.limite_geracao_ia = plano.limite_geracao_ia


class _UserCrudWorkflow:
    def __init__(self, runtime: Optional["_UserCrudRuntime"] = None) -> None:
        self._runtime = runtime or _UserCrudRuntime()

    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        return self._runtime.get_user(db=db, user_id=user_id)

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return self._runtime.get_user_by_email(db=db, email=email)

    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return self._runtime.get_users(db=db, skip=skip, limit=limit)

    def create_user(self, db: Session, user: schemas.UserCreate) -> User:
        return self._runtime.create_user(db=db, user=user)

    def update_user(
        self,
        db: Session,
        db_user: User,
        user_update: Union[
            schemas.UserUpdate,
            schemas.UserUpdateByAdmin,
            schemas.UserUpdateOAuth,
        ],
    ) -> User:
        return self._runtime.update_user(db=db, db_user=db_user, user_update=user_update)

    def delete_user(self, db: Session, db_user: User) -> User:
        return self._runtime.delete_user(db=db, db_user=db_user)

    def create_user_oauth(
        self,
        db: Session,
        user_oauth: schemas.UserCreateOAuth,
        plano_id_default: Optional[int] = None,
    ) -> User:
        return self._runtime.create_user_oauth(
            db=db,
            user_oauth=user_oauth,
            plano_id_default=plano_id_default,
        )

    def get_user_by_provider(
        self,
        db: Session,
        provider: str,
        provider_user_id: str,
    ) -> Optional[User]:
        return self._runtime.get_user_by_provider(
            db=db,
            provider=provider,
            provider_user_id=provider_user_id,
        )

    def set_user_password_reset_token(
        self,
        db: Session,
        user: User,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        self._runtime.set_user_password_reset_token(
            db=db,
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def get_user_by_reset_token(self, db: Session, token_hash: str) -> Optional[User]:
        return self._runtime.get_user_by_reset_token(db=db, token_hash=token_hash)

    def get_role(self, db: Session, role_id: int) -> Optional[Role]:
        return self._runtime.get_role(db=db, role_id=role_id)

    def get_role_by_name(self, db: Session, name: str) -> Optional[Role]:
        return self._runtime.get_role_by_name(db=db, name=name)

    def get_roles(self, db: Session, skip: int = 0, limit: int = 10) -> List[Role]:
        return self._runtime.get_roles(db=db, skip=skip, limit=limit)

    def create_role(self, db: Session, role: schemas.RoleCreate) -> Role:
        return self._runtime.create_role(db=db, role=role)

    def get_plano(self, db: Session, plano_id: int) -> Optional[Plano]:
        return self._runtime.get_plano(db=db, plano_id=plano_id)

    def get_plano_by_name(self, db: Session, nome: str) -> Optional[Plano]:
        return self._runtime.get_plano_by_name(db=db, nome=nome)

    def get_planos(self, db: Session, skip: int = 0, limit: int = 10) -> List[Plano]:
        return self._runtime.get_planos(db=db, skip=skip, limit=limit)

    def create_plano(self, db: Session, plano: schemas.PlanoCreate) -> Plano:
        return self._runtime.create_plano(db=db, plano=plano)

    def update_plano(
        self,
        db: Session,
        db_plano: Plano,
        plano_update: schemas.PlanoUpdate,
    ) -> Plano:
        return self._runtime.update_plano(db=db, db_plano=db_plano, plano_update=plano_update)

    def delete_plano(self, db: Session, db_plano: Plano) -> Plano:
        return self._runtime.delete_plano(db=db, db_plano=db_plano)


class _UserCrudRuntime:
    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def create_user(self, db: Session, user: schemas.UserCreate) -> User:
        hashed_password = security.get_password_hash(user.password)
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            nome_completo=user.nome_completo,
            idioma_preferido=user.idioma_preferido,
            chave_openai_pessoal=user.chave_openai_pessoal,
            chave_google_gemini_pessoal=user.chave_google_gemini_pessoal,
            is_active=True,
            is_superuser=False,
        )
        _apply_default_plan_limits(db_user)

        if user.plano_id:
            plano = self.get_plano(db=db, plano_id=user.plano_id)
            if plano:
                db_user.plano_id = plano.id
                db_user.limite_produtos = plano.limite_produtos
                db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
                db_user.limite_geracao_ia = plano.limite_geracao_ia
            else:
                logger.warning(
                    "Plano ID %s nao encontrado ao criar usuario %s. Usando defaults.",
                    user.plano_id,
                    user.email,
                )

        db.add(db_user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            logger.warning("Falha ao criar usuario, email duplicado: %s", user.email)
            raise HTTPException(
                status_code=400,
                detail="Um usuario com este email ja existe.",
            ) from exc
        db.refresh(db_user)
        return db_user

    def update_user(
        self,
        db: Session,
        db_user: User,
        user_update: Union[
            schemas.UserUpdate,
            schemas.UserUpdateByAdmin,
            schemas.UserUpdateOAuth,
        ],
    ) -> User:
        update_data = user_update.model_dump(exclude_unset=True)

        if update_data.get("password"):
            db_user.hashed_password = security.get_password_hash(update_data["password"])
            del update_data["password"]

        if "plano_id" in update_data:
            _apply_plano_limits(db=db, db_user=db_user, plano_id=update_data["plano_id"])
            update_data.pop("plano_id", None)

        for field, value in update_data.items():
            if hasattr(db_user, field):
                setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)
        return db_user

    def delete_user(self, db: Session, db_user: User) -> User:
        db.delete(db_user)
        db.commit()
        return db_user

    def create_user_oauth(
        self,
        db: Session,
        user_oauth: schemas.UserCreateOAuth,
        plano_id_default: Optional[int] = None,
    ) -> User:
        db_user = User(
            email=user_oauth.email,
            nome_completo=user_oauth.nome_completo,
            provider=user_oauth.provider,
            provider_user_id=user_oauth.provider_user_id,
            is_active=True,
            idioma_preferido=user_oauth.idioma_preferido,
        )
        _apply_default_plan_limits(db_user)

        if plano_id_default:
            plano = self.get_plano(db=db, plano_id=plano_id_default)
            if plano:
                db_user.plano_id = plano.id
                db_user.limite_produtos = plano.limite_produtos
                db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
                db_user.limite_geracao_ia = plano.limite_geracao_ia

        default_role = self.get_role_by_name(db=db, name="user")
        if default_role:
            db_user.role_id = default_role.id

        db.add(db_user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            logger.warning(
                "Falha ao criar usuario OAuth, email duplicado: %s",
                user_oauth.email,
            )
            raise HTTPException(
                status_code=400,
                detail="Um usuario com este email ja existe.",
            ) from exc
        db.refresh(db_user)
        return db_user

    def get_user_by_provider(
        self,
        db: Session,
        provider: str,
        provider_user_id: str,
    ) -> Optional[User]:
        return (
            db.query(User)
            .filter(User.provider == provider, User.provider_user_id == provider_user_id)
            .first()
        )

    def set_user_password_reset_token(
        self,
        db: Session,
        user: User,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        user.reset_password_token = token_hash
        user.reset_password_token_expires_at = expires_at
        db.commit()
        db.refresh(user)

    def get_user_by_reset_token(self, db: Session, token_hash: str) -> Optional[User]:
        return db.query(User).filter(User.reset_password_token == token_hash).first()

    def get_role(self, db: Session, role_id: int) -> Optional[Role]:
        return db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, db: Session, name: str) -> Optional[Role]:
        return db.query(Role).filter(Role.name == name).first()

    def get_roles(self, db: Session, skip: int = 0, limit: int = 10) -> List[Role]:
        return db.query(Role).offset(skip).limit(limit).all()

    def create_role(self, db: Session, role: schemas.RoleCreate) -> Role:
        db_role = Role(name=role.name, description=role.description)
        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        return db_role

    def get_plano(self, db: Session, plano_id: int) -> Optional[Plano]:
        return db.query(Plano).filter(Plano.id == plano_id).first()

    def get_plano_by_name(self, db: Session, nome: str) -> Optional[Plano]:
        return db.query(Plano).filter(Plano.nome == nome).first()

    def get_planos(self, db: Session, skip: int = 0, limit: int = 10) -> List[Plano]:
        return db.query(Plano).offset(skip).limit(limit).all()

    def create_plano(self, db: Session, plano: schemas.PlanoCreate) -> Plano:
        db_plano = Plano(**plano.model_dump())
        db.add(db_plano)
        db.commit()
        db.refresh(db_plano)
        return db_plano

    def update_plano(
        self,
        db: Session,
        db_plano: Plano,
        plano_update: schemas.PlanoUpdate,
    ) -> Plano:
        update_data = plano_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_plano, key, value)
        db.commit()
        db.refresh(db_plano)
        return db_plano

    def delete_plano(self, db: Session, db_plano: Plano) -> Plano:
        db.delete(db_plano)
        db.commit()
        return db_plano


_user_crud_workflow = _UserCrudWorkflow()
UserCrudWorkflow = _UserCrudWorkflow


def get_user_crud_workflow() -> UserCrudWorkflow:
    return _user_crud_workflow

