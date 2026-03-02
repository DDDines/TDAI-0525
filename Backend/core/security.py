"""Module security.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError
from Backend.core.config import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

class TokenPayload(BaseModel):
    """Class TokenPayload.

    Encapsulates one responsibility in the backend architecture.
    """
    sub: Optional[str] = None
    user_id: Optional[int] = None

class SecurityWorkflow:

    """Class SecurityWorkflow.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, runtime: Optional['SecurityRuntime']=None) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._runtime = runtime or SecurityRuntime()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Execute verify_password.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.verify_password(plain_password=plain_password, hashed_password=hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Execute get_password_hash.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.get_password_hash(password=password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta]=None) -> str:
        """Execute create_access_token.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.create_access_token(data=data, expires_delta=expires_delta)

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta]=None) -> str:
        """Execute create_refresh_token.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.create_refresh_token(data=data, expires_delta=expires_delta)

    def decode_token(self, token: str, secret_key: str) -> Optional[TokenPayload]:
        """Execute decode_token.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.decode_token(token=token, secret_key=secret_key)

class SecurityRuntime:
    """Runtime OO para operaÃ§Ãµes de hash e token JWT."""

    def verify_password(self, *, plain_password: str, hashed_password: str) -> bool:
        """Execute verify_password.

        This callable is documented to make behavior explicit for readers.
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, *, password: str) -> str:
        """Execute get_password_hash.

        This callable is documented to make behavior explicit for readers.
        """
        return pwd_context.hash(password)

    def create_access_token(self, *, data: dict, expires_delta: Optional[timedelta]=None) -> str:
        """Execute create_access_token.

        This callable is documented to make behavior explicit for readers.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta if expires_delta else datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({'exp': expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    def create_refresh_token(self, *, data: dict, expires_delta: Optional[timedelta]=None) -> str:
        """Execute create_refresh_token.

        This callable is documented to make behavior explicit for readers.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta if expires_delta else datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({'exp': expire, 'token_type': 'refresh'})
        return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, *, token: str, secret_key: str) -> Optional[TokenPayload]:
        """Execute decode_token.

        This callable is documented to make behavior explicit for readers.
        """
        try:
            payload_dict = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
            raw_user_id = payload_dict.get('user_id')
            user_id = int(raw_user_id) if raw_user_id is not None else None
            return TokenPayload(sub=payload_dict.get('sub'), user_id=user_id)
        except (JWTError, ValidationError, ValueError):
            return None
