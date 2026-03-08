from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from Backend.core.config import settings
from Backend import initial_data as initial_data_module
from Backend.initial_data import InitialDataRuntime, InitialDataWorkflow


class _UserRepoStub:
    def __init__(self):
        self.roles = {}
        self.planos = {}
        self.users = {}
        self.created_roles = []
        self.created_planos = []
        self.created_users = []

    def get_role_by_name(self, *, name):
        return self.roles.get(name)

    def create_role(self, *, role):
        created = SimpleNamespace(id=len(self.created_roles) + 1, name=role.name)
        self.roles[created.name] = created
        self.created_roles.append(created)
        return created

    def get_plano_by_name(self, *, nome):
        return self.planos.get(nome)

    def create_plano(self, *, plano):
        created = SimpleNamespace(id=len(self.created_planos) + 1, nome=plano.nome)
        self.planos[created.nome] = created
        self.created_planos.append(created)
        return created

    def get_user_by_email(self, *, email):
        return self.users.get(email)

    def create_user(self, *, user):
        created = SimpleNamespace(
            id=99,
            email=user.email,
            is_superuser=False,
            role_id=None,
        )
        self.users[created.email] = created
        self.created_users.append(created)
        return created


class _ProductTypeRepoStub:
    def __init__(self, *, existing=None, failures=None):
        self.existing = existing or {}
        self.failures = failures or {}
        self.created = []

    def get_product_type_by_key_name(self, *, key_name, user_id):
        _ = user_id
        return self.existing.get(key_name)

    def create_product_type(self, *, product_type_create, user_id):
        _ = user_id
        failure = self.failures.get(product_type_create.key_name)
        if failure:
            raise failure
        self.created.append(product_type_create.key_name)
        return SimpleNamespace(key_name=product_type_create.key_name)


class _FornecedorRepoStub:
    def __init__(self):
        self.created = []

    def create_fornecedor(self, *, fornecedor, user_id):
        self.created.append((fornecedor.nome, user_id))


class _ProductRepoStub:
    def __init__(self):
        self.created = []

    def create_produto(self, *, produto, user_id):
        self.created.append((produto.nome_base, user_id))


class _QueryChain:
    def __init__(self, *, first=None, count_value=0):
        self._first = first
        self._count_value = count_value

    def filter(self, *args):
        _ = args
        return self

    def first(self):
        return self._first

    def count(self):
        return self._count_value


class _SessionStub:
    def __init__(self):
        self.commits = 0
        self.refreshed = []
        self.query_map = {}

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)

    def query(self, model):
        return self.query_map[model]


def test_ensure_default_roles_and_plans_skip_existing_entries():
    user_repo = _UserRepoStub()
    user_repo.roles["admin"] = SimpleNamespace(name="admin")
    user_repo.planos["Gratuito"] = SimpleNamespace(nome="Gratuito")

    admin_role, user_role = InitialDataRuntime._ensure_default_roles(user_repo=user_repo)
    InitialDataRuntime._ensure_default_plans(user_repo=user_repo)

    assert admin_role.name == "admin"
    assert user_role.name == "user"
    assert [role.name for role in user_repo.created_roles] == ["user"]
    assert [plano.nome for plano in user_repo.created_planos] == ["Pro"]


def test_ensure_admin_user_returns_existing_or_creates_without_role_or_plan():
    runtime = InitialDataRuntime()
    user_repo = _UserRepoStub()
    existing = SimpleNamespace(email=settings.FIRST_SUPERUSER_EMAIL)
    user_repo.users[settings.FIRST_SUPERUSER_EMAIL] = existing
    session = _SessionStub()

    assert runtime._ensure_admin_user(session=session, user_repo=user_repo) is existing

    user_repo = _UserRepoStub()
    created = runtime._ensure_admin_user(session=session, user_repo=user_repo)

    assert created.email == settings.FIRST_SUPERUSER_EMAIL
    assert created.is_superuser is True
    assert created.role_id is None
    assert session.commits == 1
    assert session.refreshed[-1] is created


def test_ensure_admin_user_assigns_role_when_admin_role_exists():
    runtime = InitialDataRuntime()
    user_repo = _UserRepoStub()
    user_repo.roles["admin"] = SimpleNamespace(id=5, name="admin")
    user_repo.planos["Pro"] = SimpleNamespace(id=8, nome="Pro")
    session = _SessionStub()

    created = runtime._ensure_admin_user(session=session, user_repo=user_repo)

    assert created.role_id == 5


def test_ensure_global_product_types_handles_existing_integrity_and_generic_errors(caplog):
    repo = _ProductTypeRepoStub(
        existing={"eletronicos": SimpleNamespace(key_name="eletronicos")},
        failures={
            "vestuario": Exception("falha generica"),
        },
    )

    InitialDataRuntime._ensure_global_product_types(product_type_repo=repo)

    assert repo.created == []

    repo = _ProductTypeRepoStub(
        failures={
            "eletronicos": IntegrityError("stmt", "params", Exception("dup")),
            "vestuario": Exception("falha generica"),
        }
    )
    with caplog.at_level("WARNING"):
        InitialDataRuntime._ensure_global_product_types(product_type_repo=repo)

    assert "Nao foi possivel criar o tipo de produto global 'eletronicos'" in caplog.text
    assert "Erro inesperado ao criar tipo de produto global 'vestuario'" in caplog.text


def test_ensure_global_product_types_success_and_default_supplier_creation():
    repo = _ProductTypeRepoStub()
    fornecedor_repo = _FornecedorRepoStub()
    session = _SessionStub()
    session.query_map = {
        __import__("Backend.models", fromlist=["Fornecedor"]).Fornecedor: _QueryChain(first=None),
    }

    InitialDataRuntime._ensure_global_product_types(product_type_repo=repo)
    InitialDataRuntime._ensure_default_supplier(
        session=session,
        admin_user=SimpleNamespace(id=9),
        fornecedor_repo=fornecedor_repo,
    )

    assert repo.created == ["eletronicos", "vestuario"]
    assert fornecedor_repo.created == [("UouU", 9)]


def test_ensure_default_supplier_and_product_cover_early_returns():
    session = _SessionStub()
    fornecedor_repo = _FornecedorRepoStub()
    product_repo = _ProductRepoStub()
    user_repo = _UserRepoStub()

    InitialDataRuntime._ensure_default_supplier(
        session=session,
        admin_user=None,
        fornecedor_repo=fornecedor_repo,
    )
    assert fornecedor_repo.created == []

    session.query_map = {
        __import__("Backend.models", fromlist=["Fornecedor"]).Fornecedor: _QueryChain(first=SimpleNamespace(id=1)),
        __import__("Backend.models", fromlist=["Produto"]).Produto: _QueryChain(count_value=1),
    }
    InitialDataRuntime._ensure_default_supplier(
        session=session,
        admin_user=SimpleNamespace(id=5),
        fornecedor_repo=fornecedor_repo,
    )
    InitialDataRuntime._ensure_default_product(
        session=session,
        user_repo=user_repo,
        product_repo=product_repo,
    )
    assert fornecedor_repo.created == []
    assert product_repo.created == []

    session.query_map[__import__("Backend.models", fromlist=["Produto"]).Produto] = _QueryChain(count_value=0)
    InitialDataRuntime._ensure_default_product(
        session=session,
        user_repo=user_repo,
        product_repo=product_repo,
    )
    assert product_repo.created == []

    user_repo.users[settings.FIRST_SUPERUSER_EMAIL] = SimpleNamespace(id=7)
    InitialDataRuntime._ensure_default_product(
        session=session,
        user_repo=user_repo,
        product_repo=product_repo,
    )
    assert product_repo.created == [("Produto de Exemplo", 7)]


def test_initial_data_entrypoint_delegates_to_workflow(monkeypatch):
    class _WorkflowStub:
        def create_initial_data(self, *, session):
            return {"session": session}

    monkeypatch.setattr(
        "Backend.initial_data.InitialDataWorkflow",
        lambda: _WorkflowStub(),
    )

    assert initial_data_module._InitialDataEntryPoints.create_initial_data(session="db") == {"session": "db"}


def test_initial_data_workflow_and_runtime_create_initial_data(monkeypatch):
    user_repo = object()
    product_type_repo = object()
    fornecedor_repo = object()
    product_repo = object()
    calls = []

    monkeypatch.setattr("Backend.initial_data.UserRepository", lambda session: user_repo)
    monkeypatch.setattr("Backend.initial_data.ProductTypeRepository", lambda session: product_type_repo)
    monkeypatch.setattr("Backend.initial_data.FornecedorRepository", lambda session: fornecedor_repo)
    monkeypatch.setattr("Backend.initial_data.ProductRepository", lambda session: product_repo)
    monkeypatch.setattr(
        InitialDataRuntime,
        "_ensure_default_roles",
        staticmethod(lambda *, user_repo: calls.append(("roles", user_repo))),
    )
    monkeypatch.setattr(
        InitialDataRuntime,
        "_ensure_default_plans",
        staticmethod(lambda *, user_repo: calls.append(("plans", user_repo))),
    )
    monkeypatch.setattr(
        InitialDataRuntime,
        "_ensure_admin_user",
        lambda self, *, session, user_repo: calls.append(("admin", session, user_repo)) or "admin-user",
    )
    monkeypatch.setattr(
        InitialDataRuntime,
        "_ensure_global_product_types",
        staticmethod(lambda *, product_type_repo: calls.append(("types", product_type_repo))),
    )
    monkeypatch.setattr(
        InitialDataRuntime,
        "_ensure_default_supplier",
        staticmethod(
            lambda *, session, admin_user, fornecedor_repo: calls.append(
                ("supplier", session, admin_user, fornecedor_repo)
            )
        ),
    )
    monkeypatch.setattr(
        InitialDataRuntime,
        "_ensure_default_product",
        staticmethod(
            lambda *, session, user_repo, product_repo: calls.append(
                ("product", session, user_repo, product_repo)
            )
        ),
    )

    workflow = InitialDataWorkflow()
    assert workflow.create_initial_data(session="db") is None
    assert calls == [
        ("roles", user_repo),
        ("plans", user_repo),
        ("admin", "db", user_repo),
        ("types", product_type_repo),
        ("supplier", "db", "admin-user", fornecedor_repo),
        ("product", "db", user_repo, product_repo),
    ]
