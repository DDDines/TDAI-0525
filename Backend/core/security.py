from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from Backend.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[int] = None


class _SecurityWorkflow:
    def __init__(self, runtime: Optional["_SecurityRuntime"] = None) -> None:
        self._runtime = runtime or _SecurityRuntime()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self._runtime.verify_password(
            plain_password=plain_password,
            hashed_password=hashed_password,
        )

    def get_password_hash(self, password: str) -> str:
        return self._runtime.get_password_hash(password=password)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        return self._runtime.create_access_token(
            data=data,
            expires_delta=expires_delta,
        )

    def create_refresh_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        return self._runtime.create_refresh_token(
            data=data,
            expires_delta=expires_delta,
        )

    def decode_token(self, token: str, secret_key: str) -> Optional[TokenPayload]:
        return self._runtime.decode_token(token=token, secret_key=secret_key)


class _SecurityRuntime:
    """Runtime OO para operaÃ§Ãµes de hash e token JWT."""

    def verify_password(self, *, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, *, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(
        self,
        *,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        to_encode = data.copy()
        expire = (
            datetime.now(timezone.utc) + expires_delta
            if expires_delta
            else datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    def create_refresh_token(
        self,
        *,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        to_encode = data.copy()
        expire = (
            datetime.now(timezone.utc) + expires_delta
            if expires_delta
            else datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        to_encode.update({"exp": expire, "token_type": "refresh"})
        return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, *, token: str, secret_key: str) -> Optional[TokenPayload]:
        try:
            payload_dict = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
            raw_user_id = payload_dict.get("user_id")
            user_id = int(raw_user_id) if raw_user_id is not None else None
            return TokenPayload(sub=payload_dict.get("sub"), user_id=user_id)
        except (JWTError, ValidationError, ValueError):
            return None

SecurityWorkflow = _SecurityWorkflow


def get_security_workflow() -> SecurityWorkflow:
    return SecurityWorkflow()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_security_workflow().verify_password(
        plain_password=plain_password,
        hashed_password=hashed_password,
    )


def get_password_hash(password: str) -> str:
    return get_security_workflow().get_password_hash(password=password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return get_security_workflow().create_access_token(
        data=data,
        expires_delta=expires_delta,
    )


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return get_security_workflow().create_refresh_token(
        data=data,
        expires_delta=expires_delta,
    )


def decode_token(token: str, secret_key: str) -> Optional[TokenPayload]:
    return get_security_workflow().decode_token(token=token, secret_key=secret_key)




