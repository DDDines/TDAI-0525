from datetime import timedelta

from Backend.core import security
from Backend.core.config import settings


def test_password_hash_and_verify():
    password = "s3cr3t"
    hashed = security.get_password_hash(password)
    assert security.verify_password(password, hashed)


def test_access_token_flow():
    data = {"sub": "test@example.com", "user_id": 1}
    token = security.create_access_token(data, expires_delta=timedelta(minutes=1))
    payload = security.decode_token(token, settings.SECRET_KEY)
    assert payload is not None
    assert payload.sub == data["sub"]
    assert payload.user_id == data["user_id"]
