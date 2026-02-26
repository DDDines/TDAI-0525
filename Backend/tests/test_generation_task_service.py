from __future__ import annotations

import types

import pytest

from Backend.application.services.generation_task_service import GenerationTaskService


class _UserStub:
    def __init__(self, user_id: int = 1, is_superuser: bool = False) -> None:
        self.id = user_id
        self.is_superuser = is_superuser


class _ProdutoStub:
    def __init__(self, *, produto_id: int = 10, user_id: int = 1) -> None:
        self.id = produto_id
        self.user_id = user_id
        self.log_processamento = []
        self.titulos_sugeridos = None
        self.descricao_chat_api = None
        self.status_titulo_ia = None
        self.status_descricao_ia = None


class _CrudUsersStub:
    def __init__(self, user: _UserStub | None) -> None:
        self._user = user

    def get_user(self, db, user_id: int):
        return self._user


class _CrudProdutosStub:
    def __init__(self, produto: _ProdutoStub | None) -> None:
        self._produto = produto
        self.updates = []

    def get_produto(self, db, produto_id: int):
        return self._produto

    def update_produto(self, db, *, db_produto, produto_update):
        payload = vars(produto_update)
        self.updates.append(payload)
        for key, value in payload.items():
            setattr(db_produto, key, value)
        return db_produto


class _FakeSession:
    def close(self):
        return None


def _db_session_factory():
    return _FakeSession()


def _build_models_stub():
    return types.SimpleNamespace(
        StatusGeracaoIAEnum=types.SimpleNamespace(
            EM_PROGRESSO="EM_PROGRESSO",
            CONCLUIDO="CONCLUIDO",
            FALHA="FALHA",
        )
    )


def _build_schemas_stub():
    class _ProdutoUpdate:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    return types.SimpleNamespace(ProdutoUpdate=_ProdutoUpdate)


class _LoggerStub:
    def __init__(self):
        self.logs = []

    def info(self, *args, **kwargs):
        self.logs.append(("info", args, kwargs))

    def warning(self, *args, **kwargs):
        self.logs.append(("warning", args, kwargs))

    def error(self, *args, **kwargs):
        self.logs.append(("error", args, kwargs))

    def exception(self, *args, **kwargs):
        self.logs.append(("exception", args, kwargs))


@pytest.mark.asyncio
async def test_generation_task_service_marks_success_for_titulo():
    produto = _ProdutoStub()
    crud_produtos = _CrudProdutosStub(produto)
    service = GenerationTaskService(
        crud_users=_CrudUsersStub(_UserStub()),
        crud_produtos=crud_produtos,
        models=_build_models_stub(),
        schemas=_build_schemas_stub(),
        logger=_LoggerStub(),
    )

    async def _fake_generation(**kwargs):
        return ["Titulo 1", "Titulo 2"]

    await service.run_generation_task(
        db_session_factory=_db_session_factory,
        user_id=1,
        produto_id=10,
        tipo_geracao_principal="titulo",
        funcao_geracao_ia_no_servico=_fake_generation,
    )

    assert produto.status_titulo_ia == "CONCLUIDO"
    assert produto.titulos_sugeridos == ["Titulo 1", "Titulo 2"]
    assert len(crud_produtos.updates) >= 2


@pytest.mark.asyncio
async def test_generation_task_service_marks_failure_for_empty_result():
    produto = _ProdutoStub()
    crud_produtos = _CrudProdutosStub(produto)
    service = GenerationTaskService(
        crud_users=_CrudUsersStub(_UserStub()),
        crud_produtos=crud_produtos,
        models=_build_models_stub(),
        schemas=_build_schemas_stub(),
        logger=_LoggerStub(),
    )

    async def _fake_generation(**kwargs):
        return ""

    await service.run_generation_task(
        db_session_factory=_db_session_factory,
        user_id=1,
        produto_id=10,
        tipo_geracao_principal="descricao",
        funcao_geracao_ia_no_servico=_fake_generation,
    )

    assert produto.status_descricao_ia == "FALHA"

