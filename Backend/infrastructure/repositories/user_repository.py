"""User repository.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Union

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.core import security
from Backend.core.config import settings
from Backend.models import Plano, Role, User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository OO de usuarios, roles e planos com Session por request."""

    def __init__(self, db: Session) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._db = db
        self._security_workflow = security.SecurityWorkflow()

    @staticmethod
    def _apply_default_plan_limits(db_user: User) -> None:
        """Process Apply default plan limits."""
        db_user.limite_produtos = settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO
        db_user.limite_enriquecimento_web = settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO
        db_user.limite_geracao_ia = settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO

    def _apply_plano_limits(self, *, db_user: User, plano_id: Optional[int]) -> None:
        """Process Apply plano limits."""
        if plano_id is None:
            db_user.plano_id = None
            self._apply_default_plan_limits(db_user)
            db_user.data_expiracao_plano = None
            return

        plano = self.get_plano(plano_id=plano_id)
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

    def get_user(self, *, user_id: int) -> Optional[User]:
        """Return User."""
        return self._db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, *, email: str) -> Optional[User]:
        """Return User by email."""
        return self._db.query(User).filter(User.email == email).first()

    def get_users(self, *, skip: int = 0, limit: int = 100) -> List[User]:
        """Return Users."""
        return self._db.query(User).offset(skip).limit(limit).all()

    def search_users_by_email(self, *, query_text: Optional[str], limit: int) -> List[User]:
        """Return users filtered by email for admin search endpoint."""
        query = self._db.query(User)
        if query_text:
            term = f"%{query_text.lower()}%"
            query = query.filter(func.lower(User.email).ilike(term))
        return query.order_by(User.created_at.desc()).limit(limit).all()

    def create_user(self, *, user: schemas.UserCreate) -> User:
        """Create user."""
        hashed_password = self._security_workflow.get_password_hash(user.password)
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
        self._apply_default_plan_limits(db_user)

        if user.plano_id:
            plano = self.get_plano(plano_id=user.plano_id)
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

        self._db.add(db_user)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            logger.warning("Falha ao criar usuario, email duplicado: %s", user.email)
            raise HTTPException(
                status_code=400,
                detail="Um usuario com este email ja existe.",
            ) from exc
        self._db.refresh(db_user)
        return db_user

    def update_user(
        self,
        *,
        db_user: User,
        user_update: Union[
            schemas.UserUpdate,
            schemas.UserUpdateByAdmin,
            schemas.UserUpdateOAuth,
        ],
    ) -> User:
        """Update user."""
        update_data = user_update.model_dump(exclude_unset=True)

        if update_data.get("password"):
            db_user.hashed_password = self._security_workflow.get_password_hash(update_data["password"])
            del update_data["password"]

        if "plano_id" in update_data:
            self._apply_plano_limits(db_user=db_user, plano_id=update_data["plano_id"])
            update_data.pop("plano_id", None)

        for field, value in update_data.items():
            if hasattr(db_user, field):
                setattr(db_user, field, value)

        self._db.commit()
        self._db.refresh(db_user)
        return db_user

    def delete_user(self, *, db_user: User) -> User:
        """Delete user."""
        self._db.delete(db_user)
        self._db.commit()
        return db_user

    def create_user_oauth(
        self,
        *,
        user_oauth: schemas.UserCreateOAuth,
        plano_id_default: Optional[int] = None,
    ) -> User:
        """Create user oauth."""
        db_user = User(
            email=user_oauth.email,
            nome_completo=user_oauth.nome_completo,
            provider=user_oauth.provider,
            provider_user_id=user_oauth.provider_user_id,
            is_active=True,
            idioma_preferido=user_oauth.idioma_preferido,
        )
        self._apply_default_plan_limits(db_user)

        if plano_id_default:
            plano = self.get_plano(plano_id=plano_id_default)
            if plano:
                db_user.plano_id = plano.id
                db_user.limite_produtos = plano.limite_produtos
                db_user.limite_enriquecimento_web = plano.limite_enriquecimento_web
                db_user.limite_geracao_ia = plano.limite_geracao_ia

        default_role = self.get_role_by_name(name="user")
        if default_role:
            db_user.role_id = default_role.id

        self._db.add(db_user)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            logger.warning(
                "Falha ao criar usuario OAuth, email duplicado: %s",
                user_oauth.email,
            )
            raise HTTPException(
                status_code=400,
                detail="Um usuario com este email ja existe.",
            ) from exc
        self._db.refresh(db_user)
        return db_user

    def get_user_by_provider(
        self,
        *,
        provider: str,
        provider_user_id: str,
    ) -> Optional[User]:
        """Return User by provider."""
        return (
            self._db.query(User)
            .filter(User.provider == provider, User.provider_user_id == provider_user_id)
            .first()
        )

    def set_user_password_reset_token(
        self,
        *,
        user: User,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        """Process Set user password reset token."""
        user.reset_password_token = token_hash
        user.reset_password_token_expires_at = expires_at
        self._db.commit()
        self._db.refresh(user)

    def get_user_by_reset_token(self, *, token_hash: str) -> Optional[User]:
        """Return User by reset token."""
        return self._db.query(User).filter(User.reset_password_token == token_hash).first()

    def get_role(self, *, role_id: int) -> Optional[Role]:
        """Return Role."""
        return self._db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, *, name: str) -> Optional[Role]:
        """Return Role by name."""
        return self._db.query(Role).filter(Role.name == name).first()

    def get_roles(self, *, skip: int = 0, limit: int = 10) -> List[Role]:
        """Return Roles."""
        return self._db.query(Role).offset(skip).limit(limit).all()

    def create_role(self, *, role: schemas.RoleCreate) -> Role:
        """Create role."""
        db_role = Role(name=role.name, description=role.description)
        self._db.add(db_role)
        self._db.commit()
        self._db.refresh(db_role)
        return db_role

    def get_plano(self, *, plano_id: int) -> Optional[Plano]:
        """Return Plano."""
        return self._db.query(Plano).filter(Plano.id == plano_id).first()

    def get_plano_by_name(self, *, nome: str) -> Optional[Plano]:
        """Return Plano by name."""
        return self._db.query(Plano).filter(Plano.nome == nome).first()

    def get_planos(self, *, skip: int = 0, limit: int = 10) -> List[Plano]:
        """Return Planos."""
        return self._db.query(Plano).offset(skip).limit(limit).all()

    def create_plano(self, *, plano: schemas.PlanoCreate) -> Plano:
        """Create plano."""
        db_plano = Plano(**plano.model_dump())
        self._db.add(db_plano)
        self._db.commit()
        self._db.refresh(db_plano)
        return db_plano

    def update_plano(
        self,
        *,
        db_plano: Plano,
        plano_update: schemas.PlanoUpdate,
    ) -> Plano:
        """Update plano."""
        update_data = plano_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_plano, key, value)
        self._db.commit()
        self._db.refresh(db_plano)
        return db_plano

    def delete_plano(self, *, db_plano: Plano) -> Plano:
        """Delete plano."""
        self._db.delete(db_plano)
        self._db.commit()
        return db_plano
