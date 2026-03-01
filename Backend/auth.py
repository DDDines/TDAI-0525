# Backend/auth.py
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from authlib.integrations.starlette_client import OAuth, OAuthError  # type: ignore
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.config import Config as AuthlibConfig

from Backend import models
from Backend import schemas
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.core.security import pwd_context
from Backend.database import get_db
from Backend.infrastructure.repositories.user_repository import UserRepository

logger = get_logger(__name__)

PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- Configuracao OAuth social ---
auth_config_dict_env: Dict[str, str] = {}
if settings.GOOGLE_CLIENT_ID:
    auth_config_dict_env["GOOGLE_CLIENT_ID"] = settings.GOOGLE_CLIENT_ID
if settings.GOOGLE_CLIENT_SECRET:
    auth_config_dict_env["GOOGLE_CLIENT_SECRET"] = settings.GOOGLE_CLIENT_SECRET
if settings.FACEBOOK_CLIENT_ID:
    auth_config_dict_env["FACEBOOK_CLIENT_ID"] = settings.FACEBOOK_CLIENT_ID
if settings.FACEBOOK_CLIENT_SECRET:
    auth_config_dict_env["FACEBOOK_CLIENT_SECRET"] = settings.FACEBOOK_CLIENT_SECRET

oauth = OAuth(config=AuthlibConfig(environ=auth_config_dict_env))

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    if "google" not in oauth._clients:
        oauth.register(
            name="google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            client_kwargs={"scope": "openid email profile"},
        )
else:
    logger.warning(
        "Credenciais do Google OAuth (CLIENT_ID ou CLIENT_SECRET) nao configuradas no .env. Login com Google desabilitado."
    )

if settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET:
    if "facebook" not in oauth._clients:
        oauth.register(
            name="facebook",
            client_id=settings.FACEBOOK_CLIENT_ID,
            client_secret=settings.FACEBOOK_CLIENT_SECRET,
            authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
            access_token_url="https://graph.facebook.com/v19.0/oauth/access_token",
            userinfo_endpoint="https://graph.facebook.com/me?fields=id,name,email,first_name,last_name,picture",
            client_kwargs={"scope": "email public_profile"},
        )
else:
    logger.warning(
        "Credenciais do Facebook OAuth (CLIENT_ID ou CLIENT_SECRET) nao configuradas no .env. Login com Facebook desabilitado."
    )


class _AuthWorkflow:
    def __init__(self, runtime: Optional["_AuthRuntime"] = None) -> None:
        self._runtime = runtime or _AuthRuntime()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self._runtime.verify_password(
            plain_password=plain_password,
            hashed_password=hashed_password,
        )

    def get_password_hash(self, password: str) -> str:
        return self._runtime.get_password_hash(password=password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        return self._runtime.create_access_token(data=data, expires_delta=expires_delta)

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        return self._runtime.create_refresh_token(data=data, expires_delta=expires_delta)

    def create_password_reset_token(self) -> str:
        return self._runtime.create_password_reset_token()

    def hash_password_reset_token(self, token: str) -> str:
        return self._runtime.hash_password_reset_token(token=token)

    def verify_password_reset_token(self, token: str, token_hash: str) -> bool:
        return self._runtime.verify_password_reset_token(token=token, token_hash=token_hash)

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[models.User]:
        return self._runtime.authenticate_user(db=db, email=email, password=password)

    async def get_current_user(self, token: str, db: Session) -> models.User:
        return await self._runtime.get_current_user(token=token, db=db)

    def get_current_active_user(self, current_user: models.User) -> models.User:
        return self._runtime.get_current_active_user(current_user=current_user)

    async def login_for_access_token(
        self,
        form_data: OAuth2PasswordRequestForm,
        db: Session,
    ) -> Dict[str, str]:
        return await self._runtime.login_for_access_token(form_data=form_data, db=db)

    async def refresh_access_token(
        self,
        refresh_token_data: schemas.RefreshTokenRequest,
        db: Session,
    ) -> Dict[str, str]:
        return await self._runtime.refresh_access_token(refresh_token_data=refresh_token_data, db=db)

    async def update_users_me(
        self,
        user_update: schemas.UserUpdate,
        current_user: models.User,
        db: Session,
    ) -> models.User:
        return await self._runtime.update_users_me(
            user_update=user_update,
            current_user=current_user,
            db=db,
        )

    async def change_password_me(
        self,
        payload: schemas.UserChangePassword,
        current_user: models.User,
        db: Session,
    ) -> Dict[str, str]:
        return await self._runtime.change_password_me(
            payload=payload,
            current_user=current_user,
            db=db,
        )

    async def process_google_login(
        self,
        db: Session,
        google_userinfo: Dict[str, Any],
    ) -> Optional[models.User]:
        return await self._runtime.process_google_login(db=db, google_userinfo=google_userinfo)

    async def process_facebook_login(
        self,
        db: Session,
        facebook_userinfo: Dict[str, Any],
    ) -> Optional[models.User]:
        return await self._runtime.process_facebook_login(
            db=db,
            facebook_userinfo=facebook_userinfo,
        )


class _AuthRuntime:
    @staticmethod
    def _users(db: Session) -> UserRepository:
        return UserRepository(db)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = (
            datetime.now(timezone.utc) + expires_delta
            if expires_delta
            else datetime.now(timezone.utc)
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = (
            datetime.now(timezone.utc) + expires_delta
            if expires_delta
            else datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

    def create_password_reset_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_password_reset_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_password_reset_token(self, token: str, token_hash: str) -> bool:
        return self.hash_password_reset_token(token=token) == token_hash

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[models.User]:
        user = self._users(db).get_user_by_email(email=email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not user.hashed_password or not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def get_current_user(self, token: str, db: Session) -> models.User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao foi possivel validar as credenciais",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: Optional[str] = payload.get("sub")
            user_id: Optional[int] = payload.get("user_id")
            if email is None or user_id is None:
                raise credentials_exception
            token_data = schemas.TokenData(email=email, user_id=user_id)
        except JWTError:
            raise credentials_exception

        user = self._users(db).get_user(user_id=token_data.user_id)
        if user is None or user.email != token_data.email:
            raise credentials_exception
        return user

    def get_current_active_user(self, current_user: models.User) -> models.User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inativo")
        return current_user

    async def login_for_access_token(
        self,
        form_data: OAuth2PasswordRequestForm,
        db: Session,
    ) -> Dict[str, str]:
        user = self.authenticate_user(db, email=form_data.username, password=form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conta inativa.")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires,
        )
        refresh_token = self.create_refresh_token(data={"sub": user.email, "user_id": user.id})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(
        self,
        refresh_token_data: schemas.RefreshTokenRequest,
        db: Session,
    ) -> Dict[str, str]:
        token = refresh_token_data.refresh_token
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token,
                settings.REFRESH_SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            email: Optional[str] = payload.get("sub")
            user_id: Optional[int] = payload.get("user_id")
            if email is None or user_id is None:
                raise credentials_exception

            user = self._users(db).get_user(user_id=user_id)
            if not user or user.email != email or not user.is_active:
                raise credentials_exception

            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            new_access_token = self.create_access_token(
                data={"sub": user.email, "user_id": user.id},
                expires_delta=access_token_expires,
            )
            return {
                "access_token": new_access_token,
                "refresh_token": token,
                "token_type": "bearer",
            }

        except JWTError:
            raise credentials_exception

    async def update_users_me(
        self,
        user_update: schemas.UserUpdate,
        current_user: models.User,
        db: Session,
    ) -> models.User:
        update_data = user_update.model_dump(exclude_unset=True)

        if "password" in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use o endpoint de alteracao de senha para atualizar a senha.",
            )

        new_email = update_data.get("email")
        if new_email and new_email != current_user.email:
            existing = self._users(db).get_user_by_email(email=new_email)
            if existing and existing.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ja existe um usuario com este email.",
                )

        return self._users(db).update_user(
            db_user=current_user,
            user_update=user_update,
        )

    async def change_password_me(
        self,
        payload: schemas.UserChangePassword,
        current_user: models.User,
        db: Session,
    ) -> Dict[str, str]:
        if not current_user.hashed_password or not self.verify_password(
            payload.current_password,
            current_user.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta.",
            )

        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ser diferente da senha atual.",
            )

        current_user.hashed_password = self.get_password_hash(payload.new_password)
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return {"message": "Senha alterada com sucesso."}

    async def _get_or_create_social_user(
        self,
        db: Session,
        email: str,
        nome: Optional[str],
        provider: str,
        provider_user_id: str,
    ) -> Optional[models.User]:
        db_user = self._users(db).get_user_by_email(email=email)
        if db_user:
            if not db_user.is_active:
                logger.warning("Usuario existente %s (via %s) esta inativo.", email, provider)
                return None

            updated = False
            if not db_user.nome_completo and nome:
                db_user.nome_completo = nome
                updated = True
            if not db_user.provider:
                db_user.provider = provider
                updated = True
            if not db_user.provider_user_id:
                db_user.provider_user_id = provider_user_id
                updated = True

            if updated:
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
            return db_user

        default_plano = self._users(db).get_plano_by_name(nome="Gratuito")

        user_in_create = schemas.UserCreateOAuth(
            email=email,
            nome_completo=(nome or email.split("@")[0]),
            provider=provider,
            provider_user_id=provider_user_id,
        )

        created_user = self._users(db).create_user_oauth(
            user_oauth=user_in_create,
            plano_id_default=default_plano.id if default_plano else None,
        )
        logger.info("Novo usuario criado via %s: %s", provider, email)
        return created_user

    async def process_google_login(
        self,
        db: Session,
        google_userinfo: Dict[str, Any],
    ) -> Optional[models.User]:
        email = google_userinfo.get("email")
        if not email:
            logger.error("Email do Google nao encontrado nas informacoes do usuario.")
            return None

        if not google_userinfo.get("email_verified", False):
            logger.warning("Email %s do Google nao esta verificado.", email)
            return None

        nome_completo = google_userinfo.get("name")
        if not nome_completo:
            primeiro_nome = google_userinfo.get("given_name", "")
            ultimo_nome = google_userinfo.get("family_name", "")
            nome_completo = f"{primeiro_nome} {ultimo_nome}".strip()

        google_user_id = google_userinfo.get("sub")
        if not google_user_id:
            logger.error("ID de usuario do Google (sub) nao encontrado.")
            return None

        return await self._get_or_create_social_user(
            db=db,
            email=email,
            nome=nome_completo,
            provider="Google",
            provider_user_id=google_user_id,
        )

    async def process_facebook_login(
        self,
        db: Session,
        facebook_userinfo: Dict[str, Any],
    ) -> Optional[models.User]:
        email = facebook_userinfo.get("email")
        if not email:
            logger.error(
                "Email do Facebook nao fornecido. Nao e possivel prosseguir com login/registro baseado em email."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email nao fornecido pelo Facebook. Verifique suas permissoes.",
            )

        nome_completo = facebook_userinfo.get("name", "")
        facebook_user_id = facebook_userinfo.get("id")
        if not facebook_user_id:
            logger.error("ID de usuario do Facebook nao encontrado.")
            return None

        return await self._get_or_create_social_user(
            db=db,
            email=email,
            nome=nome_completo,
            provider="Facebook",
            provider_user_id=facebook_user_id,
        )

AuthWorkflow = _AuthWorkflow


def get_auth_workflow() -> AuthWorkflow:
    return AuthWorkflow()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_auth_workflow().verify_password(
        plain_password=plain_password,
        hashed_password=hashed_password,
    )


def get_password_hash(password: str) -> str:
    return get_auth_workflow().get_password_hash(password=password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return get_auth_workflow().create_access_token(
        data=data,
        expires_delta=expires_delta,
    )


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return get_auth_workflow().create_refresh_token(
        data=data,
        expires_delta=expires_delta,
    )


def create_password_reset_token() -> str:
    return get_auth_workflow().create_password_reset_token()


def hash_password_reset_token(token: str) -> str:
    return get_auth_workflow().hash_password_reset_token(token=token)


def verify_password_reset_token(token: str, token_hash: str) -> bool:
    return get_auth_workflow().verify_password_reset_token(
        token=token,
        token_hash=token_hash,
    )


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    return get_auth_workflow().authenticate_user(db=db, email=email, password=password)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    return await get_auth_workflow().get_current_user(token=token, db=db)


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    return get_auth_workflow().get_current_active_user(current_user=current_user)


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return await get_auth_workflow().login_for_access_token(form_data=form_data, db=db)


@router.post("/token/refresh/", response_model=schemas.Token)
async def refresh_access_token(
    refresh_token_data: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    return await get_auth_workflow().refresh_access_token(
        refresh_token_data=refresh_token_data,
        db=db,
    )


@router.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user


@router.put("/users/me", response_model=schemas.UserResponse)
async def update_users_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return await get_auth_workflow().update_users_me(
        user_update=user_update,
        current_user=current_user,
        db=db,
    )


@router.put("/users/me/change-password")
async def change_password_me(
    payload: schemas.UserChangePassword,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return await get_auth_workflow().change_password_me(
        payload=payload,
        current_user=current_user,
        db=db,
    )


async def process_google_login(db: Session, google_userinfo: Dict[str, Any]) -> Optional[models.User]:
    return await get_auth_workflow().process_google_login(
        db=db,
        google_userinfo=google_userinfo,
    )


async def process_facebook_login(db: Session, facebook_userinfo: Dict[str, Any]) -> Optional[models.User]:
    return await get_auth_workflow().process_facebook_login(
        db=db,
        facebook_userinfo=facebook_userinfo,
    )




