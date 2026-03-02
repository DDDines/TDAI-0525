"""Fluxo de autenticacao e autorizacao HTTP com contratos OO."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import hashlib
import secrets

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.config import Config as AuthlibConfig

from Backend import models
from Backend import schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.core.security import pwd_context
from Backend.infrastructure.repositories.user_repository import UserRepository


logger = get_logger(__name__)
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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
        "Credenciais do Google OAuth (CLIENT_ID ou CLIENT_SECRET) nao configuradas no .env. "
        "Login com Google desabilitado."
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
        "Credenciais do Facebook OAuth (CLIENT_ID ou CLIENT_SECRET) nao configuradas no .env. "
        "Login com Facebook desabilitado."
    )


class AuthRuntime:
    """Runtime OO responsavel por integracoes e operacoes de auth."""

    def __init__(
        self,
        *,
        session: Optional[Session] = None,
        user_repository: Optional[UserRepository] = None,
    ) -> None:
        """Initialize dependencies used by this component."""
        self._session = session
        self._user_repository = user_repository or (
            UserRepository(session) if session is not None else None
        )

    def _require_user_repository(self) -> UserRepository:
        """Handle Require user repository in this request workflow."""
        if self._user_repository is None:
            raise RuntimeError("AuthRuntime requires a session-bound UserRepository.")
        return self._user_repository

    def _require_session(self) -> Session:
        """Handle Require session in this request workflow."""
        if self._session is None:
            raise RuntimeError("AuthRuntime requires a session for write operations.")
        return self._session

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Handle Verify password in this request workflow."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Return Password hash."""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token."""
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
        """Create refresh token."""
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
        """Create password reset token."""
        return secrets.token_urlsafe(32)

    def hash_password_reset_token(self, token: str) -> str:
        """Handle Hash password reset token in this request workflow."""
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_password_reset_token(self, token: str, token_hash: str) -> bool:
        """Handle Verify password reset token in this request workflow."""
        return self.hash_password_reset_token(token=token) == token_hash

    def authenticate_user(self, email: str, password: str) -> Optional[models.User]:
        """Handle Authenticate user in this request workflow."""
        user = self._require_user_repository().get_user_by_email(email=email)
        if not user:
            return None
        if not user.is_active:
            return None
        if not user.hashed_password or not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def get_current_user(self, token: str) -> models.User:
        """Return Current user."""
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

        user = self._require_user_repository().get_user(user_id=token_data.user_id)
        if user is None or user.email != token_data.email:
            raise credentials_exception
        return user

    @staticmethod
    def get_current_active_user(current_user: models.User) -> models.User:
        """Return Current active user."""
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inativo")
        return current_user

    async def login_for_access_token(self, form_data: OAuth2PasswordRequestForm) -> Dict[str, str]:
        """Handle Login for access token in this request workflow."""
        user = self.authenticate_user(email=form_data.username, password=form_data.password)
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
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def refresh_access_token(self, refresh_token_data: schemas.RefreshTokenRequest) -> Dict[str, str]:
        """Handle Refresh access token in this request workflow."""
        token = refresh_token_data.refresh_token
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: Optional[str] = payload.get("sub")
            user_id: Optional[int] = payload.get("user_id")
            if email is None or user_id is None:
                raise credentials_exception
            user = self._require_user_repository().get_user(user_id=user_id)
            if not user or user.email != email or (not user.is_active):
                raise credentials_exception
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            new_access_token = self.create_access_token(
                data={"sub": user.email, "user_id": user.id},
                expires_delta=access_token_expires,
            )
            return {"access_token": new_access_token, "refresh_token": token, "token_type": "bearer"}
        except JWTError:
            raise credentials_exception

    async def update_users_me(
        self,
        user_update: schemas.UserUpdate,
        current_user: models.User,
    ) -> models.User:
        """Update users me."""
        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use o endpoint de alteracao de senha para atualizar a senha.",
            )
        new_email = update_data.get("email")
        if new_email and new_email != current_user.email:
            existing = self._require_user_repository().get_user_by_email(email=new_email)
            if existing and existing.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ja existe um usuario com este email.",
                )
        return self._require_user_repository().update_user(
            db_user=current_user,
            user_update=user_update,
        )

    async def change_password_me(
        self,
        payload: schemas.UserChangePassword,
        current_user: models.User,
    ) -> Dict[str, str]:
        """Handle Change password me in this request workflow."""
        if not current_user.hashed_password or not self.verify_password(
            payload.current_password,
            current_user.hashed_password,
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ser diferente da senha atual.",
            )
        current_user.hashed_password = self.get_password_hash(payload.new_password)
        session = self._require_session()
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
        return {"message": "Senha alterada com sucesso."}

    async def _get_or_create_social_user(
        self,
        email: str,
        nome: Optional[str],
        provider: str,
        provider_user_id: str,
    ) -> Optional[models.User]:
        """Handle Get or create social user in this request workflow."""
        user_repo = self._require_user_repository()
        session = self._require_session()
        db_user = user_repo.get_user_by_email(email=email)
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
                session.add(db_user)
                session.commit()
                session.refresh(db_user)
            return db_user

        default_plano = user_repo.get_plano_by_name(nome="Gratuito")
        user_in_create = schemas.UserCreateOAuth(
            email=email,
            nome_completo=nome or email.split("@")[0],
            provider=provider,
            provider_user_id=provider_user_id,
        )
        created_user = user_repo.create_user_oauth(
            user_oauth=user_in_create,
            plano_id_default=default_plano.id if default_plano else None,
        )
        logger.info("Novo usuario criado via %s: %s", provider, email)
        return created_user

    async def process_google_login(self, google_userinfo: Dict[str, Any]) -> Optional[models.User]:
        """Handle google login in this request workflow."""
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
            email=email,
            nome=nome_completo,
            provider="Google",
            provider_user_id=google_user_id,
        )

    async def process_facebook_login(self, facebook_userinfo: Dict[str, Any]) -> Optional[models.User]:
        """Handle facebook login in this request workflow."""
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
            email=email,
            nome=nome_completo,
            provider="Facebook",
            provider_user_id=facebook_user_id,
        )


class AuthWorkflow:
    """Workflow/escopo request-scoped para o fluxo de auth."""

    def __init__(
        self,
        *,
        session: Optional[Session] = None,
        runtime: Optional[AuthRuntime] = None,
    ) -> None:
        """Initialize dependencies used by this component."""
        self._runtime = runtime or AuthRuntime(session=session)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Handle Verify password in this request workflow."""
        return self._runtime.verify_password(plain_password=plain_password, hashed_password=hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Return Password hash."""
        return self._runtime.get_password_hash(password=password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token."""
        return self._runtime.create_access_token(data=data, expires_delta=expires_delta)

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create refresh token."""
        return self._runtime.create_refresh_token(data=data, expires_delta=expires_delta)

    def create_password_reset_token(self) -> str:
        """Create password reset token."""
        return self._runtime.create_password_reset_token()

    def hash_password_reset_token(self, token: str) -> str:
        """Handle Hash password reset token in this request workflow."""
        return self._runtime.hash_password_reset_token(token=token)

    def verify_password_reset_token(self, token: str, token_hash: str) -> bool:
        """Handle Verify password reset token in this request workflow."""
        return self._runtime.verify_password_reset_token(token=token, token_hash=token_hash)

    def authenticate_user(self, email: str, password: str) -> Optional[models.User]:
        """Handle Authenticate user in this request workflow."""
        return self._runtime.authenticate_user(email=email, password=password)

    async def get_current_user(self, token: str) -> models.User:
        """Return Current user."""
        return await self._runtime.get_current_user(token=token)

    @staticmethod
    def get_current_active_user(current_user: models.User) -> models.User:
        """Return Current active user."""
        return AuthRuntime.get_current_active_user(current_user=current_user)

    async def login_for_access_token(self, form_data: OAuth2PasswordRequestForm) -> Dict[str, str]:
        """Handle Login for access token in this request workflow."""
        return await self._runtime.login_for_access_token(form_data=form_data)

    async def refresh_access_token(self, refresh_token_data: schemas.RefreshTokenRequest) -> Dict[str, str]:
        """Handle Refresh access token in this request workflow."""
        return await self._runtime.refresh_access_token(refresh_token_data=refresh_token_data)

    async def update_users_me(
        self,
        user_update: schemas.UserUpdate,
        current_user: models.User,
    ) -> models.User:
        """Update users me."""
        return await self._runtime.update_users_me(user_update=user_update, current_user=current_user)

    async def change_password_me(
        self,
        payload: schemas.UserChangePassword,
        current_user: models.User,
    ) -> Dict[str, str]:
        """Handle Change password me in this request workflow."""
        return await self._runtime.change_password_me(payload=payload, current_user=current_user)

    async def process_google_login(self, google_userinfo: Dict[str, Any]) -> Optional[models.User]:
        """Handle google login in this request workflow."""
        return await self._runtime.process_google_login(google_userinfo=google_userinfo)

    async def process_facebook_login(self, facebook_userinfo: Dict[str, Any]) -> Optional[models.User]:
        """Handle facebook login in this request workflow."""
        return await self._runtime.process_facebook_login(facebook_userinfo=facebook_userinfo)


class _AuthRequestScope:
    """Escopo request-scoped para operacoes de autenticacao HTTP."""

    def __init__(self, *, session: Session) -> None:
        """Initialize dependencies used by this component."""
        self._workflow = AuthWorkflow(session=session)

    async def get_current_user(self, *, token: str) -> models.User:
        """Return Current user."""
        return await self._workflow.get_current_user(token=token)

    async def login_for_access_token(self, *, form_data: OAuth2PasswordRequestForm):
        """Handle Login for access token in this request workflow."""
        return await self._workflow.login_for_access_token(form_data=form_data)

    async def refresh_access_token(self, *, refresh_token_data: schemas.RefreshTokenRequest):
        """Handle Refresh access token in this request workflow."""
        return await self._workflow.refresh_access_token(refresh_token_data=refresh_token_data)

    async def update_users_me(
        self,
        *,
        user_update: schemas.UserUpdate,
        current_user: models.User,
    ) -> models.User:
        """Update users me."""
        return await self._workflow.update_users_me(user_update=user_update, current_user=current_user)

    async def change_password_me(
        self,
        *,
        payload: schemas.UserChangePassword,
        current_user: models.User,
    ) -> Dict[str, str]:
        """Handle Change password me in this request workflow."""
        return await self._workflow.change_password_me(payload=payload, current_user=current_user)


_build_auth_request_scope = ServiceContainerDependencySupport.build_request_scoped_dependency(
    lambda session: _AuthRequestScope(session=session)
)


class _AuthDependencies:

    """Encapsulates Auth dependencies."""
    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        request_scope: _AuthRequestScope = Depends(_build_auth_request_scope),
    ) -> models.User:
        """Dependencia FastAPI para resolver usuario autenticado."""
        return await request_scope.get_current_user(token=token)


class _AuthActiveUserDependency:

    """Encapsulates Auth active user dependency."""
    @staticmethod
    async def get_current_active_user(
        current_user: models.User = Depends(_AuthDependencies.get_current_user),
    ) -> models.User:
        """Dependencia FastAPI que valida usuario ativo."""
        return AuthWorkflow.get_current_active_user(current_user=current_user)


class _EndpointHandlers:

    """Encapsulates Endpoint handlers."""
    @router.post("/token", response_model=schemas.Token)
    async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        request_scope: _AuthRequestScope = Depends(_build_auth_request_scope),
    ):
        """Endpoint de login por credenciais locais."""
        return await request_scope.login_for_access_token(form_data=form_data)

    @router.post("/token/refresh/", response_model=schemas.Token)
    async def refresh_access_token(
        refresh_token_data: schemas.RefreshTokenRequest,
        request_scope: _AuthRequestScope = Depends(_build_auth_request_scope),
    ):
        """Endpoint de refresh token."""
        return await request_scope.refresh_access_token(refresh_token_data=refresh_token_data)

    @router.get("/users/me", response_model=schemas.UserResponse)
    async def read_users_me(
        current_user: models.User = Depends(_AuthActiveUserDependency.get_current_active_user),
    ):
        """Retorna perfil do usuario autenticado."""
        return current_user

    @router.put("/users/me", response_model=schemas.UserResponse)
    async def update_users_me(
        user_update: schemas.UserUpdate,
        current_user: models.User = Depends(_AuthActiveUserDependency.get_current_active_user),
        request_scope: _AuthRequestScope = Depends(_build_auth_request_scope),
    ):
        """Atualiza dados de perfil do usuario autenticado."""
        return await request_scope.update_users_me(user_update=user_update, current_user=current_user)

    @router.put("/users/me/change-password")
    async def change_password_me(
        payload: schemas.UserChangePassword,
        current_user: models.User = Depends(_AuthActiveUserDependency.get_current_active_user),
        request_scope: _AuthRequestScope = Depends(_build_auth_request_scope),
    ):
        """Atualiza senha do usuario autenticado."""
        return await request_scope.change_password_me(payload=payload, current_user=current_user)
