"""Behavioral tests for MainBootstrapRuntime bootstrap and seed helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import main as main_module
from Backend.main import MainBootstrapRuntime


class _FakeSession:
    """Track database side effects produced by bootstrap helpers."""

    def __init__(self) -> None:
        self.executed = []
        self.added = []
        self.commits = 0
        self.refreshes = []
        self.rollbacks = 0
        self.query_result = None
        self.query_count_value = 0

    def execute(self, statement) -> None:
        self.executed.append(str(statement))

    def add(self, item) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, item) -> None:
        self.refreshes.append(item)

    def rollback(self) -> None:
        self.rollbacks += 1

    def query(self, *_args):
        parent = self

        class _FakeQuery:
            def filter(self, *_fargs, **_fkwargs):
                return self

            def first(self):
                return parent.query_result

            def count(self):
                return parent.query_count_value

        return _FakeQuery()


class _FakeInspector:
    """Simple inspector stub returned by sqlalchemy.inspect."""

    def __init__(self, table_names, columns):
        self._table_names = table_names
        self._columns = columns

    def get_table_names(self):
        return self._table_names

    def get_columns(self, table_name):
        return self._columns


class _FakeUserRepo:
    """Minimal user repository double for bootstrap tests."""

    def __init__(self) -> None:
        self.users_by_email = {}
        self.roles = {}
        self.planos = {}
        self.created_roles = []
        self.created_planos = []
        self.created_users = []

    def get_user_by_email(self, *, email):
        return self.users_by_email.get(email)

    def create_user(self, *, user):
        created = SimpleNamespace(
            id=501,
            email=user.email,
            plano_id=user.plano_id,
            is_superuser=False,
            role_id=None,
            limite_produtos=None,
            limite_enriquecimento_web=None,
            limite_geracao_ia=None,
        )
        self.created_users.append(created)
        self.users_by_email[created.email] = created
        return created

    def get_role_by_name(self, *, name):
        return self.roles.get(name)

    def create_role(self, *, role):
        created = SimpleNamespace(id=len(self.created_roles) + 1, name=role.name)
        self.created_roles.append(created)
        self.roles[created.name] = created
        return created

    def get_plano_by_name(self, *, nome):
        return self.planos.get(nome)

    def create_plano(self, *, plano):
        created = SimpleNamespace(
            id=len(self.created_planos) + 10,
            nome=plano.nome,
            limite_produtos=plano.limite_produtos,
            limite_enriquecimento_web=plano.limite_enriquecimento_web,
            limite_geracao_ia=plano.limite_geracao_ia,
        )
        self.created_planos.append(created)
        self.planos[created.nome] = created
        return created


class _FakeProductTypeRepo:
    """Repository stub used to capture default product-type seeding."""

    def __init__(self) -> None:
        self.by_key = {}
        self.created = []

    def get_product_type_by_key_name(self, *, key_name, user_id=None):
        return self.by_key.get((key_name, user_id))

    def create_product_type(self, *, product_type_create, user_id=None):
        created = SimpleNamespace(
            id=len(self.created) + 1,
            key_name=product_type_create.key_name,
            friendly_name=product_type_create.friendly_name,
            user_id=user_id,
        )
        self.created.append(created)
        self.by_key[(created.key_name, user_id)] = created
        return created


class _FakeFornecedorRepo:
    """Repository stub used to capture default supplier seeding."""

    def __init__(self) -> None:
        self.created = []

    def create_fornecedor(self, *, fornecedor, user_id):
        self.created.append((fornecedor, user_id))
        return SimpleNamespace(id=801, nome=fornecedor.nome, user_id=user_id)


class _FakeProductRepo:
    """Repository stub used to capture default product seeding."""

    def __init__(self) -> None:
        self.created = []

    def create_produto(self, *, produto, user_id):
        self.created.append((produto, user_id))
        return SimpleNamespace(id=901, nome_base=produto.nome_base, user_id=user_id)


def test_build_allowed_origins_merges_environment_and_defaults(monkeypatch):
    """CORS origin resolution should normalize env values and keep safe defaults."""
    runtime = MainBootstrapRuntime()
    monkeypatch.setattr(
        main_module.settings,
        "BACKEND_CORS_ORIGINS",
        ["https://catalog.ai", "https://catalog.ai/"],
        raising=False,
    )

    origins = runtime.build_allowed_origins()

    assert "http://localhost:5173" in origins
    assert "https://catalog.ai" in origins
    assert "https://catalog.ai/" in origins

    monkeypatch.setattr(main_module.settings, "BACKEND_CORS_ORIGINS", None, raising=False)
    assert "http://127.0.0.1:5173" in runtime.build_allowed_origins()


def test_ensure_static_files_path_creates_the_missing_directory(monkeypatch, tmp_path):
    """Static directory bootstrap should create the target folder when absent."""
    fake_main_file = tmp_path / "main.py"
    fake_main_file.write_text("# test")
    fake_static_dir = tmp_path / "static"
    assert not fake_static_dir.exists()
    monkeypatch.setattr(main_module, "__file__", str(fake_main_file))

    static_path = MainBootstrapRuntime().ensure_static_files_path()

    assert static_path == fake_static_dir
    assert static_path.exists()


def test_ensure_legacy_user_profile_columns_covers_create_skip_and_rollback(monkeypatch):
    """Legacy column migration should add missing columns, skip when not needed and rollback on error."""
    session = _FakeSession()
    monkeypatch.setattr(
        main_module,
        "inspect",
        lambda engine: _FakeInspector(["users"], [{"name": "id"}]),
    )
    MainBootstrapRuntime._ensure_legacy_user_profile_columns(session=session)
    assert any("nome_empresa" in statement for statement in session.executed)
    assert any("avatar_url" in statement for statement in session.executed)
    assert session.commits == 1

    session = _FakeSession()
    monkeypatch.setattr(
        main_module,
        "inspect",
        lambda engine: _FakeInspector(["users"], [{"name": "id"}, {"name": "nome_empresa"}, {"name": "avatar_url"}]),
    )
    MainBootstrapRuntime._ensure_legacy_user_profile_columns(session=session)
    assert session.executed == []
    assert session.commits == 0

    session = _FakeSession()
    monkeypatch.setattr(
        main_module,
        "inspect",
        lambda engine: (_ for _ in ()).throw(RuntimeError("falha-inspector")),
    )
    MainBootstrapRuntime._ensure_legacy_user_profile_columns(session=session)
    assert session.rollbacks == 1


def test_role_and_plan_bootstrap_create_missing_records_and_apply_fallbacks():
    """Role/plan bootstrap should create missing defaults and expose fallback references."""
    repo = _FakeUserRepo()

    admin_role, user_role = MainBootstrapRuntime._ensure_roles(user_repo=repo)
    assert admin_role.name == "admin"
    assert user_role.name == "user"
    assert len(repo.created_roles) == 2

    admin_plano, plano_gratuito = MainBootstrapRuntime._ensure_planos(user_repo=repo)
    assert admin_plano.nome == "Pro"
    assert plano_gratuito.nome == "Gratuito"
    assert len(repo.created_planos) == 2

    class _FakeUserRepoWithoutPro(_FakeUserRepo):
        def create_plano(self, *, plano):
            if plano.nome == "Pro":
                created = SimpleNamespace(
                    id=99,
                    nome="Outro",
                    limite_produtos=plano.limite_produtos,
                    limite_enriquecimento_web=plano.limite_enriquecimento_web,
                    limite_geracao_ia=plano.limite_geracao_ia,
                )
                self.created_planos.append(created)
                return created
            return super().create_plano(plano=plano)

    repo_sem_pro = _FakeUserRepoWithoutPro()
    repo_sem_pro.planos["Gratuito"] = SimpleNamespace(
        id=1,
        nome="Gratuito",
        limite_produtos=10,
        limite_enriquecimento_web=10,
        limite_geracao_ia=10,
    )
    admin_plano, plano_gratuito = MainBootstrapRuntime._ensure_planos(user_repo=repo_sem_pro)
    assert admin_plano is plano_gratuito


def test_admin_user_bootstrap_covers_create_update_and_missing_role(monkeypatch):
    """Admin bootstrap should create new admins, update existing ones and reject missing role."""
    runtime = MainBootstrapRuntime()
    session = _FakeSession()
    repo = _FakeUserRepo()
    plano_pro = SimpleNamespace(
        id=33,
        nome="Pro",
        limite_produtos=1000,
        limite_enriquecimento_web=500,
        limite_geracao_ia=2000,
    )
    plano_gratuito = SimpleNamespace(id=11, nome="Gratuito")
    repo.planos["Pro"] = plano_pro
    repo.planos["Gratuito"] = plano_gratuito
    admin_role = SimpleNamespace(id=9, name="admin")

    monkeypatch.setattr(main_module.settings, "ADMIN_EMAIL", "admin@test.com", raising=False)
    monkeypatch.setattr(main_module.settings, "ADMIN_PASSWORD", "adminpass", raising=False)
    monkeypatch.setattr(main_module.settings, "ADMIN_IDIOMA_PREFERIDO", "pt-BR", raising=False)

    created = runtime._ensure_admin_user(
        session=session,
        user_repo=repo,
        admin_role_obj=admin_role,
        admin_plano_obj=plano_pro,
        plano_gratuito_obj=plano_gratuito,
    )
    assert created.email == "admin@test.com"
    assert created.role_id == 9
    assert created.is_superuser is True
    assert created.plano_id == 33
    assert session.commits == 1
    assert session.refreshes == [created]

    existing = SimpleNamespace(
        id=77,
        email="admin@test.com",
        role_id=None,
        is_superuser=False,
        plano_id=None,
    )
    repo.users_by_email["admin@test.com"] = existing
    session = _FakeSession()
    updated = runtime._ensure_admin_user(
        session=session,
        user_repo=repo,
        admin_role_obj=admin_role,
        admin_plano_obj=plano_pro,
        plano_gratuito_obj=plano_gratuito,
    )
    assert updated is existing
    assert updated.role_id == 9
    assert updated.is_superuser is True
    assert updated.plano_id == 33
    assert session.commits == 1

    repo.users_by_email.clear()
    session = _FakeSession()
    assert (
        runtime._ensure_admin_user(
            session=session,
            user_repo=repo,
            admin_role_obj=None,
            admin_plano_obj=plano_pro,
            plano_gratuito_obj=plano_gratuito,
        )
        is None
    )


def test_default_seed_helpers_cover_existing_and_creation_paths():
    """Bootstrap helpers should seed only when the catalog or owner state requires it."""
    product_type_repo = _FakeProductTypeRepo()
    MainBootstrapRuntime._ensure_global_product_types(product_type_repo=product_type_repo)
    assert {item.key_name for item in product_type_repo.created} == {"eletronicos", "vestuario"}
    MainBootstrapRuntime._ensure_global_product_types(product_type_repo=product_type_repo)
    assert len(product_type_repo.created) == 2

    session = _FakeSession()
    fornecedor_repo = _FakeFornecedorRepo()
    admin_user = SimpleNamespace(id=55)
    MainBootstrapRuntime._ensure_default_supplier(
        session=session,
        admin_user=None,
        fornecedor_repo=fornecedor_repo,
    )
    assert fornecedor_repo.created == []

    session.query_result = None
    MainBootstrapRuntime._ensure_default_supplier(
        session=session,
        admin_user=admin_user,
        fornecedor_repo=fornecedor_repo,
    )
    assert fornecedor_repo.created[0][0].nome == "UouU"
    assert fornecedor_repo.created[0][1] == 55

    session = _FakeSession()
    product_repo = _FakeProductRepo()
    MainBootstrapRuntime._ensure_default_product(
        session=session,
        admin_user=None,
        product_repo=product_repo,
    )
    assert product_repo.created == []

    session.query_count_value = 0
    MainBootstrapRuntime._ensure_default_product(
        session=session,
        admin_user=admin_user,
        product_repo=product_repo,
    )
    assert product_repo.created[0][0].nome_base == "Produto de Exemplo"

    session = _FakeSession()
    session.query_count_value = 2
    MainBootstrapRuntime._ensure_default_product(
        session=session,
        admin_user=admin_user,
        product_repo=product_repo,
    )
    assert len(product_repo.created) == 1


def test_assign_default_role_and_plan_and_create_user_cover_error_paths():
    """User creation should assign fallback role/plan and reject duplicates or missing role."""
    runtime = MainBootstrapRuntime()
    repo = _FakeUserRepo()
    repo.planos["Gratuito"] = SimpleNamespace(id=7, nome="Gratuito")
    repo.roles["user"] = SimpleNamespace(id=4, name="user")
    payload = SimpleNamespace(email="novo@test.com", plano_id=None, role_id=None)

    runtime._assign_default_role_and_plan(user_repo=repo, user_in=payload)
    assert payload.plano_id == 7
    assert payload.role_id == 4

    repo_sem_role = _FakeUserRepo()
    with pytest.raises(HTTPException) as exc_info:
        runtime._assign_default_role_and_plan(
            user_repo=repo_sem_role,
            user_in=SimpleNamespace(email="x@test.com", plano_id=None, role_id=None),
        )
    assert exc_info.value.status_code == 500

    class _RuntimeWithRepo(MainBootstrapRuntime):
        def __init__(self, user_repo):
            self._user_repo = user_repo

        def create_new_user(self, *, user_in, session):
            user_repo = self._user_repo
            if user_repo.get_user_by_email(email=user_in.email):
                raise HTTPException(status_code=400, detail="Um usuario com este email ja existe no sistema.")
            self._assign_default_role_and_plan(user_repo=user_repo, user_in=user_in)
            return user_repo.create_user(user=user_in)

    session = _FakeSession()
    repo_para_criacao = _FakeUserRepo()
    repo_para_criacao.planos["Gratuito"] = SimpleNamespace(id=7, nome="Gratuito")
    repo_para_criacao.roles["user"] = SimpleNamespace(id=4, name="user")
    user_payload = SimpleNamespace(email="create@test.com", plano_id=None, role_id=None)
    created_user = _RuntimeWithRepo(repo_para_criacao).create_new_user(
        user_in=user_payload,
        session=session,
    )
    assert created_user.email == "create@test.com"
    assert user_payload.plano_id == 7
    assert user_payload.role_id == 4

    repo_com_duplicado = _FakeUserRepo()
    repo_com_duplicado.users_by_email["dup@test.com"] = SimpleNamespace(id=1, email="dup@test.com")

    with pytest.raises(HTTPException) as exc_info:
        _RuntimeWithRepo(repo_com_duplicado).create_new_user(
            user_in=SimpleNamespace(email="dup@test.com", plano_id=None, role_id=None),
            session=session,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_startup_event_create_defaults_closes_session_and_handles_failures(monkeypatch):
    """Startup bootstrap should close the session even when the seed flow raises."""
    calls = []
    session = SimpleNamespace(close=lambda: calls.append("close"))
    monkeypatch.setattr(main_module, "SessionLocal", lambda: session)
    monkeypatch.setattr(main_module.settings, "AUTO_CREATE_TABLES", False, raising=False)

    runtime = MainBootstrapRuntime()
    runtime._ensure_legacy_user_profile_columns = lambda session: calls.append("legacy")
    runtime._ensure_roles = lambda user_repo: (SimpleNamespace(id=1), None)
    runtime._ensure_planos = lambda user_repo: (SimpleNamespace(id=2), SimpleNamespace(id=3))
    runtime._ensure_admin_user = lambda **kwargs: calls.append("admin") or SimpleNamespace(id=9)
    runtime._ensure_global_product_types = lambda product_type_repo: calls.append("types")
    runtime._ensure_default_supplier = lambda **kwargs: calls.append("supplier")
    runtime._ensure_default_product = lambda **kwargs: calls.append("product")

    await runtime.startup_event_create_defaults()
    assert calls[:6] == ["legacy", "admin", "types", "supplier", "product", "close"]

    calls.clear()
    runtime._ensure_legacy_user_profile_columns = lambda session: (_ for _ in ()).throw(RuntimeError("boom"))
    await runtime.startup_event_create_defaults()
    assert calls == ["close"]
