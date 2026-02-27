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


def _verify_password_impl(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _get_password_hash_impl(password: str) -> str:
    return pwd_context.hash(password)


def _create_access_token_impl(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def _create_refresh_token_impl(
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


def _decode_token_impl(token: str, secret_key: str) -> Optional[TokenPayload]:
    try:
        payload_dict = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        raw_user_id = payload_dict.get("user_id")
        user_id = int(raw_user_id) if raw_user_id is not None else None
        return TokenPayload(sub=payload_dict.get("sub"), user_id=user_id)
    except (JWTError, ValidationError, ValueError):
        return None


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
    """Runtime OO para operações de hash e token JWT."""

    def verify_password(self, *, plain_password: str, hashed_password: str) -> bool:
        return _verify_password_impl(
            plain_password=plain_password,
            hashed_password=hashed_password,
        )

    def get_password_hash(self, *, password: str) -> str:
        return _get_password_hash_impl(password=password)

    def create_access_token(
        self,
        *,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        return _create_access_token_impl(data=data, expires_delta=expires_delta)

    def create_refresh_token(
        self,
        *,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        return _create_refresh_token_impl(data=data, expires_delta=expires_delta)

    def decode_token(self, *, token: str, secret_key: str) -> Optional[TokenPayload]:
        return _decode_token_impl(token=token, secret_key=secret_key)


security_runtime = _SecurityRuntime()
_security_workflow = _SecurityWorkflow(runtime=security_runtime)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _security_workflow.verify_password(
        plain_password=plain_password,
        hashed_password=hashed_password,
    )


def get_password_hash(password: str) -> str:
    return _security_workflow.get_password_hash(password=password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return _security_workflow.create_access_token(
        data=data,
        expires_delta=expires_delta,
    )


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return _security_workflow.create_refresh_token(
        data=data,
        expires_delta=expires_delta,
    )


def decode_token(token: str, secret_key: str) -> Optional[TokenPayload]:
    return _security_workflow.decode_token(token=token, secret_key=secret_key)


class SecurityLegacyService:
    def verify_password(self, *args, **kwargs):
        return verify_password(*args, **kwargs)

    def get_password_hash(self, *args, **kwargs):
        return get_password_hash(*args, **kwargs)

    def create_access_token(self, *args, **kwargs):
        return create_access_token(*args, **kwargs)

    def create_refresh_token(self, *args, **kwargs):
        return create_refresh_token(*args, **kwargs)

    def decode_token(self, *args, **kwargs):
        return decode_token(*args, **kwargs)


security_legacy_service = SecurityLegacyService()
