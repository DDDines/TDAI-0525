"""Behavioral tests for AuthRuntime core workflows and edge cases."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import JWTError

from Backend import auth as auth_module
from Backend.auth import AuthRuntime


class _FakeSession:
    """Track write operations performed by AuthRuntime."""

    def __init__(self) -> None:
        self.added = []
        self.committed = 0
        self.refreshed = []

    def add(self, item) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.committed += 1

    def refresh(self, item) -> None:
        self.refreshed.append(item)


class _FakeUserRepository:
    """In-memory repository double used by AuthRuntime tests."""

    def __init__(self) -> None:
        self.users_by_email = {}
        self.users_by_id = {}
        self.updated_calls = []
        self.oauth_created = []
        self.plan_by_name = {}

    def get_user_by_email(self, *, email):
        return self.users_by_email.get(email)

    def get_user(self, *, user_id):
        return self.users_by_id.get(user_id)

    def update_user(self, *, db_user, user_update):
        self.updated_calls.append((db_user, user_update))
        return db_user

    def create_user_oauth(self, *, user_oauth, plano_id_default=None):
        created = SimpleNamespace(
            id=999,
            email=user_oauth.email,
            nome_completo=user_oauth.nome_completo,
            provider=user_oauth.provider,
            provider_user_id=user_oauth.provider_user_id,
            plano_id=plano_id_default,
            is_active=True,
        )
        self.oauth_created.append((user_oauth, plano_id_default, created))
        self.users_by_email[created.email] = created
        self.users_by_id[created.id] = created
        return created

    def get_plano_by_name(self, *, nome):
        return self.plan_by_name.get(nome)


def _build_runtime(*, session: _FakeSession | None = None, repo: _FakeUserRepository | None = None) -> AuthRuntime:
    return AuthRuntime(session=session, user_repository=repo)


def test_require_collaborators_raise_when_runtime_is_misconfigured():
    """AuthRuntime should fail fast when mandatory collaborators are absent."""
    runtime = _build_runtime()

    with pytest.raises(RuntimeError):
        runtime._require_user_repository()

    with pytest.raises(RuntimeError):
        runtime._require_session()


def test_authenticate_user_rejects_missing_inactive_or_wrong_password():
    """Authentication should stop on missing, inactive or invalid credentials."""
    repo = _FakeUserRepository()
    active = SimpleNamespace(id=1, email="user@test.com", is_active=True, hashed_password="hash")
    inactive = SimpleNamespace(id=2, email="inactive@test.com", is_active=False, hashed_password="hash")
    repo.users_by_email = {active.email: active, inactive.email: inactive}
    runtime = _build_runtime(repo=repo)
    runtime.verify_password = lambda plain_password, hashed_password: plain_password == "senha-ok"

    assert runtime.authenticate_user(email="missing@test.com", password="x") is None
    assert runtime.authenticate_user(email=inactive.email, password="senha-ok") is None
    assert runtime.authenticate_user(email=active.email, password="senha-ruim") is None
    assert runtime.authenticate_user(email=active.email, password="senha-ok") is active


@pytest.mark.asyncio
async def test_get_current_user_validates_token_payload_and_user_lookup(monkeypatch):
    """Current-user resolution should decode the token and validate repository data."""
    repo = _FakeUserRepository()
    user = SimpleNamespace(id=7, email="user@test.com", is_active=True)
    repo.users_by_id[user.id] = user
    runtime = _build_runtime(repo=repo)

    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: {"sub": "user@test.com", "user_id": 7},
    )

    resolved = await runtime.get_current_user(token="token-ok")
    assert resolved is user

    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: {"sub": None, "user_id": 7},
    )
    with pytest.raises(HTTPException) as exc_info:
        await runtime.get_current_user(token="token-sem-email")
    assert exc_info.value.status_code == 401

    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: (_ for _ in ()).throw(JWTError("bad token")),
    )
    with pytest.raises(HTTPException) as exc_info:
        await runtime.get_current_user(token="token-invalido")
    assert exc_info.value.status_code == 401


def test_get_current_active_user_rejects_inactive_users():
    """Inactive users cannot pass the active-user dependency contract."""
    active_user = SimpleNamespace(is_active=True)
    inactive_user = SimpleNamespace(is_active=False)

    assert AuthRuntime.get_current_active_user(active_user) is active_user

    with pytest.raises(HTTPException) as exc_info:
        AuthRuntime.get_current_active_user(inactive_user)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_login_and_refresh_token_workflows_cover_success_and_failure_paths(monkeypatch):
    """Login and refresh should emit tokens only for valid active users."""
    repo = _FakeUserRepository()
    user = SimpleNamespace(id=11, email="login@test.com", is_active=True, hashed_password="hash")
    repo.users_by_email[user.email] = user
    repo.users_by_id[user.id] = user
    runtime = _build_runtime(repo=repo)
    runtime.authenticate_user = lambda email, password: user if password == "ok" else None
    runtime.create_access_token = lambda data, expires_delta=None: f"access:{data['user_id']}"
    runtime.create_refresh_token = lambda data, expires_delta=None: f"refresh:{data['user_id']}"

    token_payload = await runtime.login_for_access_token(
        SimpleNamespace(username=user.email, password="ok")
    )
    assert token_payload == {
        "access_token": "access:11",
        "refresh_token": "refresh:11",
        "token_type": "bearer",
    }

    with pytest.raises(HTTPException) as exc_info:
        await runtime.login_for_access_token(SimpleNamespace(username=user.email, password="bad"))
    assert exc_info.value.status_code == 401

    inactive = SimpleNamespace(id=12, email="inactive@test.com", is_active=False, hashed_password="hash")
    runtime.authenticate_user = lambda email, password: inactive
    with pytest.raises(HTTPException) as exc_info:
        await runtime.login_for_access_token(SimpleNamespace(username=inactive.email, password="ok"))
    assert exc_info.value.status_code == 400

    runtime = _build_runtime(repo=repo)
    runtime.create_access_token = lambda data, expires_delta=None: "new-access"
    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: {"sub": user.email, "user_id": user.id},
    )
    refreshed = await runtime.refresh_access_token(
        SimpleNamespace(refresh_token="refresh-token")
    )
    assert refreshed == {
        "access_token": "new-access",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
    }

    repo.users_by_id[user.id] = SimpleNamespace(id=user.id, email="other@test.com", is_active=True)
    with pytest.raises(HTTPException) as exc_info:
        await runtime.refresh_access_token(SimpleNamespace(refresh_token="refresh-token"))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_update_users_me_rejects_password_changes_and_duplicate_email():
    """Profile updates should block password mutation and duplicate emails."""
    repo = _FakeUserRepository()
    current_user = SimpleNamespace(id=21, email="current@test.com")
    repo.users_by_email["duplicate@test.com"] = SimpleNamespace(id=99, email="duplicate@test.com")
    runtime = _build_runtime(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        await runtime.update_users_me(
            user_update=SimpleNamespace(model_dump=lambda exclude_unset=True: {"password": "x"}),
            current_user=current_user,
        )
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        await runtime.update_users_me(
            user_update=SimpleNamespace(model_dump=lambda exclude_unset=True: {"email": "duplicate@test.com"}),
            current_user=current_user,
        )
    assert exc_info.value.status_code == 400

    payload = SimpleNamespace(model_dump=lambda exclude_unset=True: {"nome_completo": "Atualizado"})
    updated = await runtime.update_users_me(user_update=payload, current_user=current_user)
    assert updated is current_user
    assert repo.updated_calls == [(current_user, payload)]


@pytest.mark.asyncio
async def test_change_password_me_validates_current_password_and_persists_hash():
    """Password changes should validate the current secret and persist the new hash."""
    session = _FakeSession()
    current_user = SimpleNamespace(id=5, hashed_password="hash-atual")
    runtime = _build_runtime(session=session, repo=_FakeUserRepository())
    runtime.verify_password = lambda plain_password, hashed_password: plain_password == "senha-atual"
    runtime.get_password_hash = lambda password: f"hash:{password}"

    with pytest.raises(HTTPException) as exc_info:
        await runtime.change_password_me(
            payload=SimpleNamespace(current_password="errada", new_password="nova"),
            current_user=current_user,
        )
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        await runtime.change_password_me(
            payload=SimpleNamespace(current_password="senha-atual", new_password="senha-atual"),
            current_user=current_user,
        )
    assert exc_info.value.status_code == 400

    result = await runtime.change_password_me(
        payload=SimpleNamespace(current_password="senha-atual", new_password="nova-segura"),
        current_user=current_user,
    )
    assert result == {"message": "Senha alterada com sucesso."}
    assert current_user.hashed_password == "hash:nova-segura"
    assert session.committed == 1
    assert session.added == [current_user]
    assert session.refreshed == [current_user]


@pytest.mark.asyncio
async def test_get_or_create_social_user_updates_existing_or_creates_new_user():
    """Social login should update missing profile data or create a fresh OAuth user."""
    session = _FakeSession()
    repo = _FakeUserRepository()
    repo.plan_by_name["Gratuito"] = SimpleNamespace(id=17, nome="Gratuito")
    existing = SimpleNamespace(
        id=31,
        email="social@test.com",
        is_active=True,
        nome_completo=None,
        provider=None,
        provider_user_id=None,
    )
    repo.users_by_email[existing.email] = existing
    repo.users_by_id[existing.id] = existing
    runtime = _build_runtime(session=session, repo=repo)

    updated = await runtime._get_or_create_social_user(
        email=existing.email,
        nome="Pessoa Social",
        provider="Google",
        provider_user_id="sub-123",
    )
    assert updated is existing
    assert existing.nome_completo == "Pessoa Social"
    assert existing.provider == "Google"
    assert existing.provider_user_id == "sub-123"
    assert session.committed == 1

    inactive = SimpleNamespace(
        id=32,
        email="inactive-social@test.com",
        is_active=False,
        nome_completo=None,
        provider=None,
        provider_user_id=None,
    )
    repo.users_by_email[inactive.email] = inactive
    assert (
        await runtime._get_or_create_social_user(
            email=inactive.email,
            nome="Inativo",
            provider="Google",
            provider_user_id="sub-321",
        )
        is None
    )

    created = await runtime._get_or_create_social_user(
        email="novo-social@test.com",
        nome=None,
        provider="Facebook",
        provider_user_id="fb-1",
    )
    assert created.email == "novo-social@test.com"
    assert created.nome_completo == "novo-social"
    assert created.plano_id == 17
    assert repo.oauth_created


@pytest.mark.asyncio
async def test_social_login_adapters_validate_payloads_and_delegate_to_get_or_create():
    """Google and Facebook adapters should validate provider-specific payload rules."""
    runtime = _build_runtime(session=_FakeSession(), repo=_FakeUserRepository())
    recorded = []

    async def _capture(**kwargs):
        recorded.append(kwargs)
        return SimpleNamespace(id=77, email=kwargs["email"])

    runtime._get_or_create_social_user = _capture

    assert await runtime.process_google_login({"email_verified": True, "sub": "abc"}) is None
    assert await runtime.process_google_login({"email": "g@test.com", "email_verified": False, "sub": "abc"}) is None
    assert await runtime.process_google_login({"email": "g@test.com", "email_verified": True}) is None

    google_user = await runtime.process_google_login(
        {
            "email": "g@test.com",
            "email_verified": True,
            "given_name": "Gina",
            "family_name": "Silva",
            "sub": "google-1",
        }
    )
    assert google_user.email == "g@test.com"
    assert recorded[-1]["nome"] == "Gina Silva"
    assert recorded[-1]["provider"] == "Google"

    with pytest.raises(HTTPException) as exc_info:
        await runtime.process_facebook_login({"name": "Face User"})
    assert exc_info.value.status_code == 400

    assert await runtime.process_facebook_login({"email": "f@test.com", "name": "Face User"}) is None

    facebook_user = await runtime.process_facebook_login(
        {"email": "f@test.com", "name": "Face User", "id": "fb-123"}
    )
    assert facebook_user.email == "f@test.com"
    assert recorded[-1]["provider"] == "Facebook"
