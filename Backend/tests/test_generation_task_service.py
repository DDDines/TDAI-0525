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

    def get_user(self, *, user_id: int):
        return self._user


class _CrudProdutosStub:
    def __init__(self, produto: _ProdutoStub | None) -> None:
        self._produto = produto
        self.updates = []

    def get_produto(self, *, produto_id: int):
        return self._produto

    def update_produto(self, *, db_produto, produto_update):
        payload = vars(produto_update)
        self.updates.append(payload)
        for key, value in payload.items():
            setattr(db_produto, key, value)
        return db_produto


class _FakeSession:
    def close(self):
        return None


class _TopLevelFunctionSurface:

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

    def _build_service(*, produto: _ProdutoStub, user: _UserStub | None = None):
        crud_users = _CrudUsersStub(user or _UserStub())
        crud_produtos = _CrudProdutosStub(produto)
    
        class _UserRepository:
            def __init__(self, _session):
                self._stub = crud_users
    
            def get_user(self, *, user_id: int):
                return self._stub.get_user(user_id=user_id)
    
        class _ProductRepository:
            def __init__(self, _session):
                self._stub = crud_produtos
    
            def get_produto(self, *, produto_id: int):
                return self._stub.get_produto(produto_id=produto_id)
    
            def update_produto(self, *, db_produto, produto_update):
                return self._stub.update_produto(
                    db_produto=db_produto,
                    produto_update=produto_update,
                )
    
        service = GenerationTaskService(
            db_session_factory=_db_session_factory,
            user_repository_factory=_UserRepository,
            product_repository_factory=_ProductRepository,
            models=_build_models_stub(),
            schemas=_build_schemas_stub(),
            logger=_LoggerStub(),
        )
        return service, crud_produtos

    @pytest.mark.asyncio
    async def test_generation_task_service_marks_success_for_titulo():
        produto = _ProdutoStub()
        service, crud_produtos = _build_service(produto=produto)
    
        async def _fake_generation(**kwargs):
            return ["Titulo 1", "Titulo 2"]
    
        await service.run_generation_task(
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
        service, crud_produtos = _build_service(produto=produto)
    
        async def _fake_generation(**kwargs):
            return ""
    
        await service.run_generation_task(
            user_id=1,
            produto_id=10,
            tipo_geracao_principal="descricao",
            funcao_geracao_ia_no_servico=_fake_generation,
        )
    
        assert produto.status_descricao_ia == "FALHA"

_db_session_factory = _TopLevelFunctionSurface._db_session_factory
_build_models_stub = _TopLevelFunctionSurface._build_models_stub
_build_schemas_stub = _TopLevelFunctionSurface._build_schemas_stub
_build_service = _TopLevelFunctionSurface._build_service
test_generation_task_service_marks_success_for_titulo = _TopLevelFunctionSurface.test_generation_task_service_marks_success_for_titulo
test_generation_task_service_marks_failure_for_empty_result = _TopLevelFunctionSurface.test_generation_task_service_marks_failure_for_empty_result






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






