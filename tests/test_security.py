from datetime import timedelta

from Backend.core import security
from Backend.core.config import settings


class _TopLevelFunctionSurface:

    def test_password_hash_and_verify():
        password = "s3cr3t"
        workflow = security.get_security_workflow()
        hashed = workflow.get_password_hash(password)
        assert workflow.verify_password(password, hashed)

    def test_access_token_flow():
        data = {"sub": "test@example.com", "user_id": 1}
        workflow = security.get_security_workflow()
        token = workflow.create_access_token(data, expires_delta=timedelta(minutes=1))
        payload = workflow.decode_token(token, settings.SECRET_KEY)
        assert payload is not None
        assert payload.sub == data["sub"]
        assert payload.user_id == data["user_id"]

test_password_hash_and_verify = _TopLevelFunctionSurface.test_password_hash_and_verify
test_access_token_flow = _TopLevelFunctionSurface.test_access_token_flow


