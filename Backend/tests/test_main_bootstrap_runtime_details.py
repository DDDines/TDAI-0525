"""Additional branch coverage for main bootstrap runtime helpers."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from Backend import main as main_module
from Backend.main import MainBootstrapRuntime, MainBootstrapWorkflow


class _TruthyEmptyOrigins:
    def __bool__(self):
        return True

    def __iter__(self):
        return iter(())


class _BrokenOrigins:
    def __bool__(self):
        return True

    def __iter__(self):
        raise RuntimeError("boom")


class _FakeSession:
    def __init__(self) -> None:
        self.executed = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.query_result = None

    def execute(self, statement):
        self.executed.append(str(statement))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1

    def add(self, _item):
        return None

    def refresh(self, _item):
        return None

    def query(self, *_args):
        parent = self

        class _Query:
            def filter(self, *_fargs, **_fkwargs):
                return self

            def first(self):
                return parent.query_result

            def count(self):
                return 0

        return _Query()


class _FakeInspector:
    def __init__(self, table_names, columns):
        self._table_names = table_names
        self._columns = columns

    def get_table_names(self):
        return self._table_names

    def get_columns(self, _table_name):
        return self._columns


class _FakeCreateUserRepo:
    def __init__(self, *, duplicate=False, keep_created_plan=True):
        self.duplicate = duplicate
        self.keep_created_plan = keep_created_plan
        self.created_user = None

    def get_user_by_email(self, *, email):
        if self.duplicate:
            return SimpleNamespace(email=email)
        return None

    def get_plano_by_name(self, *, nome):
        if nome == "Gratuito":
            return SimpleNamespace(id=7, nome="Gratuito")
        if nome == "Pro":
            return SimpleNamespace(
                id=33,
                nome="Pro",
                limite_produtos=1000,
                limite_enriquecimento_web=500,
                limite_geracao_ia=2000,
            )
        return None

    def get_role_by_name(self, *, name):
        if name == "user":
            return SimpleNamespace(id=4, name="user")
        return None

    def create_user(self, *, user):
        self.created_user = SimpleNamespace(
            id=501,
            email=user.email,
            plano_id=user.plano_id if self.keep_created_plan else None,
            is_superuser=False,
            role_id=None,
            limite_produtos=None,
            limite_enriquecimento_web=None,
            limite_geracao_ia=None,
        )
        return self.created_user


def test_build_allowed_origins_handles_truthy_empty_iterable_and_iteration_error(monkeypatch):
    runtime = MainBootstrapRuntime()

    monkeypatch.setattr(
        main_module.settings,
        "BACKEND_CORS_ORIGINS",
        _TruthyEmptyOrigins(),
        raising=False,
    )
    origins = runtime.build_allowed_origins()
    assert "http://localhost:5173" in origins

    monkeypatch.setattr(
        main_module.settings,
        "BACKEND_CORS_ORIGINS",
        _BrokenOrigins(),
        raising=False,
    )
    origins = runtime.build_allowed_origins()
    assert "http://127.0.0.1:5173" in origins


def test_ensure_tables_and_legacy_columns_cover_error_and_missing_table(monkeypatch):
    create_calls = []

    def _raise_on_create_all(*, bind):
        create_calls.append(bind)
        raise RuntimeError("create-all-failed")

    monkeypatch.setattr(main_module.models.Base.metadata, "create_all", _raise_on_create_all)
    MainBootstrapRuntime._ensure_tables()
    assert create_calls == [main_module.engine]

    session = _FakeSession()
    monkeypatch.setattr(
        main_module,
        "inspect",
        lambda _engine: _FakeInspector([], []),
    )
    MainBootstrapRuntime._ensure_legacy_user_profile_columns(session=session)
    assert session.executed == []
    assert session.commits == 0

    create_calls.clear()
    monkeypatch.setattr(main_module.models.Base.metadata, "create_all", lambda *, bind: create_calls.append(bind))
    MainBootstrapRuntime._ensure_tables()
    assert create_calls == [main_module.engine]


def test_create_new_user_covers_duplicate_guard_and_existing_plan(monkeypatch):
    runtime = MainBootstrapRuntime()
    repo = _FakeCreateUserRepo()
    monkeypatch.setattr(main_module, "UserRepository", lambda _session: repo)

    user_in = SimpleNamespace(email="new@test.com", plano_id=99, role_id=None)
    created = runtime.create_new_user(user_in=user_in, session="db-session")
    assert created.email == "new@test.com"
    assert user_in.plano_id == 99
    assert user_in.role_id == 4

    duplicate_repo = _FakeCreateUserRepo(duplicate=True)
    monkeypatch.setattr(main_module, "UserRepository", lambda _session: duplicate_repo)
    with pytest.raises(HTTPException) as exc_info:
        runtime.create_new_user(
            user_in=SimpleNamespace(email="dup@test.com", plano_id=None, role_id=None),
            session="db-session",
        )
    assert exc_info.value.status_code == 400


def test_role_and_plan_bootstrap_cover_preexisting_and_missing_records():
    class _PreexistingRepo:
        def __init__(self):
            self.roles = {
                "admin": SimpleNamespace(id=1, name="admin"),
                "user": SimpleNamespace(id=2, name="user"),
            }
            self.planos = {
                "Gratuito": SimpleNamespace(id=11, nome="Gratuito"),
                "Pro": SimpleNamespace(id=12, nome="Pro"),
            }

        def get_role_by_name(self, *, name):
            return self.roles.get(name)

        def create_role(self, *, role):
            raise AssertionError(f"unexpected role creation: {role.name}")

        def get_plano_by_name(self, *, nome):
            return self.planos.get(nome)

        def create_plano(self, *, plano):
            raise AssertionError(f"unexpected plano creation: {plano.nome}")

    admin_role, user_role = MainBootstrapRuntime._ensure_roles(user_repo=_PreexistingRepo())
    assert admin_role.name == "admin"
    assert user_role.name == "user"

    class _BrokenRepo:
        def get_role_by_name(self, *, name):
            return None

        def create_role(self, *, role):
            return SimpleNamespace(id=99, name=f"broken-{role.name}")

        def get_plano_by_name(self, *, nome):
            return None

        def create_plano(self, *, plano):
            return SimpleNamespace(
                id=100,
                nome=f"broken-{plano.nome}",
                limite_produtos=plano.limite_produtos,
                limite_enriquecimento_web=plano.limite_enriquecimento_web,
                limite_geracao_ia=plano.limite_geracao_ia,
            )

    admin_role, user_role = MainBootstrapRuntime._ensure_roles(user_repo=_BrokenRepo())
    assert admin_role is None
    assert user_role is None

    admin_plano, plano_gratuito = MainBootstrapRuntime._ensure_planos(user_repo=_BrokenRepo())
    assert admin_plano is None
    assert plano_gratuito is None


def test_admin_user_bootstrap_covers_plan_assignment_fallbacks_and_noop_update(monkeypatch):
    runtime = MainBootstrapRuntime()
    session = _FakeSession()
    monkeypatch.setattr(main_module.settings, "ADMIN_EMAIL", "admin@test.com", raising=False)
    monkeypatch.setattr(main_module.settings, "ADMIN_PASSWORD", "adminpass", raising=False)
    monkeypatch.delattr(main_module.settings, "ADMIN_IDIOMA_PREFERIDO", raising=False)

    admin_role = SimpleNamespace(id=9, name="admin")
    plano_pro = SimpleNamespace(
        id=33,
        nome="Pro",
        limite_produtos=1000,
        limite_enriquecimento_web=500,
        limite_geracao_ia=2000,
    )
    plano_free = SimpleNamespace(id=11, nome="Gratuito")

    repo_without_plan = _FakeCreateUserRepo(keep_created_plan=False)
    created = runtime._ensure_admin_user(
        session=session,
        user_repo=repo_without_plan,
        admin_role_obj=admin_role,
        admin_plano_obj=plano_pro,
        plano_gratuito_obj=plano_free,
    )
    assert created.plano_id == plano_pro.id
    assert created.limite_produtos == 1000
    assert created.limite_enriquecimento_web == 500
    assert created.limite_geracao_ia == 2000

    session = _FakeSession()
    created_free = runtime._ensure_admin_user(
        session=session,
        user_repo=_FakeCreateUserRepo(keep_created_plan=False),
        admin_role_obj=admin_role,
        admin_plano_obj=None,
        plano_gratuito_obj=plano_free,
    )
    assert created_free.plano_id == plano_free.id

    existing_repo = _FakeCreateUserRepo()
    existing_user = SimpleNamespace(
        id=77,
        email="admin@test.com",
        role_id=admin_role.id,
        is_superuser=True,
        plano_id=plano_pro.id,
    )
    existing_repo.get_user_by_email = lambda *, email: existing_user
    existing_repo.get_plano_by_name = lambda *, nome: plano_pro if nome == "Pro" else None
    session = _FakeSession()
    updated = runtime._ensure_admin_user(
        session=session,
        user_repo=existing_repo,
        admin_role_obj=admin_role,
        admin_plano_obj=plano_pro,
        plano_gratuito_obj=plano_free,
    )
    assert updated is existing_user
    assert session.commits == 0


@pytest.mark.asyncio
async def test_startup_workflow_runtime_and_http_handlers_delegate(monkeypatch):
    session = _FakeSession()
    calls = []
    runtime = MainBootstrapRuntime()

    monkeypatch.setattr(main_module, "SessionLocal", lambda: session)
    monkeypatch.setattr(main_module.settings, "AUTO_CREATE_TABLES", True, raising=False)
    runtime._ensure_tables = lambda: calls.append("tables")
    runtime._ensure_legacy_user_profile_columns = lambda session: calls.append("legacy")
    runtime._ensure_roles = lambda user_repo: (SimpleNamespace(id=1), SimpleNamespace(id=2))
    runtime._ensure_planos = lambda user_repo: (SimpleNamespace(id=3), SimpleNamespace(id=4))
    runtime._ensure_admin_user = lambda **kwargs: calls.append("admin") or SimpleNamespace(id=9)
    runtime._ensure_global_product_types = lambda product_type_repo: calls.append("types")
    runtime._ensure_default_supplier = lambda **kwargs: calls.append("supplier")
    runtime._ensure_default_product = lambda **kwargs: calls.append("product")

    await runtime.startup_event_create_defaults()
    assert calls[:6] == ["tables", "legacy", "admin", "types", "supplier", "product"]
    assert session.closed == 1

    class _WorkflowStub:
        async def startup_event_create_defaults(self):
            calls.append("workflow-startup")

        def create_new_user(self, *, user_in, session):
            calls.append(("endpoint-create", user_in.email, session))
            return {"email": user_in.email}

    monkeypatch.setattr(main_module, "MainBootstrapWorkflow", lambda: _WorkflowStub())

    payload = SimpleNamespace(email="endpoint@test.com")
    assert MainBootstrapWorkflow(runtime=SimpleNamespace(
        build_allowed_origins=lambda: ["http://localhost:5173"],
        ensure_static_files_path=lambda: "static",
        startup_event_create_defaults=lambda: calls.append("delegated-startup"),
        create_new_user=lambda **kwargs: kwargs["user_in"],
    )).create_new_user(payload, "db") is payload

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/users/", "headers": []})
    assert main_module._EndpointHandlers.create_new_user(request, payload, "db") == {"email": "endpoint@test.com"}
    assert await main_module._EndpointHandlers.root() == {
        "message": f"Bem-vindo a API do {main_module.settings.PROJECT_NAME}!"
    }
    assert await main_module._EndpointHandlers.health_check() == {"status": "ok"}


@pytest.mark.asyncio
async def test_main_bootstrap_workflow_async_delegate():
    calls = []

    class _AsyncRuntime:
        def build_allowed_origins(self):
            return ["http://localhost:5173"]

        def ensure_static_files_path(self):
            return "static"

        async def startup_event_create_defaults(self):
            calls.append("startup")

        def create_new_user(self, **kwargs):
            return kwargs["user_in"]

    workflow = MainBootstrapWorkflow(runtime=_AsyncRuntime())
    await workflow.startup_event_create_defaults()
    assert calls == ["startup"]


def test_reloading_main_module_reexecutes_app_bootstrap():
    reloaded = importlib.reload(main_module)
    assert reloaded.app.title == reloaded.settings.PROJECT_NAME


def test_default_supplier_existing_supplier_path():
    session = _FakeSession()
    session.query_result = SimpleNamespace(id=1, nome="UouU")
    fornecedor_repo = SimpleNamespace(
        create_fornecedor=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not create"))
    )
    MainBootstrapRuntime._ensure_default_supplier(
        session=session,
        admin_user=SimpleNamespace(id=55),
        fornecedor_repo=fornecedor_repo,
    )


@pytest.mark.asyncio
async def test_lifecycle_entries_delegate_to_workflow(monkeypatch):
    calls = []

    class _Workflow:
        async def startup_event_create_defaults(self):
            calls.append("startup")

    monkeypatch.setattr(main_module, "MainBootstrapWorkflow", lambda: _Workflow())

    async with main_module.lifespan(SimpleNamespace()):
        calls.append("inside")
    await main_module._MainLifecycleEntries.startup_event_create_defaults()

    assert calls == ["startup", "inside", "startup"]
