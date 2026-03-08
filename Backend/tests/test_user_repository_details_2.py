from __future__ import annotations

from types import SimpleNamespace

from Backend.infrastructure.repositories.user_repository import UserRepository


class _DbStub:
    def __init__(self):
        self.commits = 0
        self.refreshed = []
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_apply_plano_limits_covers_found_and_missing_plan_paths():
    repo = UserRepository(_DbStub())
    db_user = SimpleNamespace(
        email="user@example.com",
        plano_id=None,
        limite_produtos=None,
        limite_enriquecimento_web=None,
        limite_geracao_ia=None,
        data_expiracao_plano="x",
    )
    plan = SimpleNamespace(
        id=7,
        limite_produtos=100,
        limite_enriquecimento_web=200,
        limite_geracao_ia=300,
    )

    repo.get_plano = lambda *, plano_id: None
    repo._apply_plano_limits(db_user=db_user, plano_id=999)
    assert db_user.plano_id is None
    assert db_user.limite_produtos is None

    repo.get_plano = lambda *, plano_id: plan
    repo._apply_plano_limits(db_user=db_user, plano_id=7)
    assert db_user.plano_id == 7
    assert db_user.limite_produtos == 100
    assert db_user.limite_enriquecimento_web == 200
    assert db_user.limite_geracao_ia == 300


def test_update_user_skips_unknown_fields_and_oauth_without_plan_or_role():
    db = _DbStub()
    repo = UserRepository(db)
    repo._security_workflow = SimpleNamespace(get_password_hash=lambda password: f"hash:{password}")

    db_user = SimpleNamespace(
        email="user@example.com",
        hashed_password="old",
        nome_completo="Old",
        plano_id=None,
        limite_produtos=1,
        limite_enriquecimento_web=2,
        limite_geracao_ia=3,
    )
    update_payload = SimpleNamespace(
        model_dump=lambda exclude_unset=True: {
            "nome_completo": "Novo",
            "password": "secret",
            "campo_que_nao_existe": "ignorar",
        }
    )

    updated = repo.update_user(db_user=db_user, user_update=update_payload)
    assert updated.nome_completo == "Novo"
    assert updated.hashed_password == "hash:secret"
    assert not hasattr(updated, "campo_que_nao_existe")

    repo.get_plano = lambda *, plano_id: None
    repo.get_role_by_name = lambda *, name: None
    user_oauth = repo.create_user_oauth(
        user_oauth=SimpleNamespace(
            email="oauth@example.com",
            nome_completo="OAuth",
            nome_empresa=None,
            avatar_url=None,
            provider="google",
            provider_user_id="gid",
            idioma_preferido="pt-BR",
        ),
        plano_id_default=None,
    )

    assert user_oauth.plano_id is None
    assert user_oauth.role_id is None
    assert db.commits == 2
