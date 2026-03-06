"""Module test generation task service.

Contains backend logic related to test generation task service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import types

import pytest

from Backend.application.services.generation_task_service import GenerationTaskService


class _UserStub:
    """Represent user stub and centralize responsibilities for this module."""
    def __init__(self, user_id: int = 1, is_superuser: bool = False) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.id = user_id
        self.is_superuser = is_superuser


class _ProdutoStub:
    """Represent produto stub and centralize responsibilities for this module."""
    def __init__(self, *, produto_id: int = 10, user_id: int = 1) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.id = produto_id
        self.user_id = user_id
        self.log_processamento = []
        self.titulos_sugeridos = None
        self.descricao_chat_api = None
        self.status_titulo_ia = None
        self.status_descricao_ia = None
        self.dados_brutos_web = {}


class _CrudUsersStub:
    """Represent crud users stub and centralize responsibilities for this module."""
    def __init__(self, user: _UserStub | None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._user = user

    def get_user(self, *, user_id: int):
        """Return user for this workflow."""
        return self._user


class _CrudProdutosStub:
    """Represent crud produtos stub and centralize responsibilities for this module."""
    def __init__(self, produto: _ProdutoStub | None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._produto = produto
        self.updates = []

    def get_produto(self, *, produto_id: int):
        """Return produto for this workflow."""
        return self._produto

    def update_produto(self, *, db_produto, produto_update):
        """Update produto for this workflow."""
        payload = vars(produto_update)
        self.updates.append(payload)
        for key, value in payload.items():
            setattr(db_produto, key, value)
        return db_produto


class _FakeSession:
    """Represent fake session and centralize responsibilities for this module."""
    def close(self):
        """Run close in this workflow."""
        return None


class _SessionProviderStub:
    """Simple OO provider to open sessions from a factory."""

    def __init__(self, factory):
        """Store session factory callable used in tests."""
        self._factory = factory

    def open_session(self):
        """Open and return a session instance."""
        return self._factory()


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _db_session_factory():
        """Run db session factory in this workflow."""
        return _FakeSession()

    def _build_models_stub():
        """Run build models stub in this workflow."""
        return types.SimpleNamespace(
            StatusGeracaoIAEnum=types.SimpleNamespace(
                EM_PROGRESSO="EM_PROGRESSO",
                CONCLUIDO="CONCLUIDO",
                FALHA="FALHA",
            )
        )

    def _build_schemas_stub():
        """Run build schemas stub in this workflow."""
        class _ProdutoUpdate:
            """Represent produto update and centralize responsibilities for this module."""
            def __init__(self, **kwargs):
                """Initialize collaborators and configuration required by this component."""
                for key, value in kwargs.items():
                    setattr(self, key, value)
    
        return types.SimpleNamespace(ProdutoUpdate=_ProdutoUpdate)

    def _build_service(*, produto: _ProdutoStub, user: _UserStub | None = None):
        """Run build service in this workflow."""
        crud_users = _CrudUsersStub(user or _UserStub())
        crud_produtos = _CrudProdutosStub(produto)
    
        class _UserRepository:
            """Represent user repository and centralize responsibilities for this module."""
            def __init__(self, _session):
                """Initialize collaborators and configuration required by this component."""
                self._stub = crud_users
    
            def get_user(self, *, user_id: int):
                """Return user for this workflow."""
                return self._stub.get_user(user_id=user_id)
    
        class _ProductRepository:
            """Represent product repository and centralize responsibilities for this module."""
            def __init__(self, _session):
                """Initialize collaborators and configuration required by this component."""
                self._stub = crud_produtos
    
            def get_produto(self, *, produto_id: int):
                """Return produto for this workflow."""
                return self._stub.get_produto(produto_id=produto_id)
    
            def update_produto(self, *, db_produto, produto_update):
                """Update produto for this workflow."""
                return self._stub.update_produto(
                    db_produto=db_produto,
                    produto_update=produto_update,
                )
    
        service = GenerationTaskService(
            session_provider=_SessionProviderStub(_db_session_factory),
            user_repository_factory=_UserRepository,
            product_repository_factory=_ProductRepository,
            models=_build_models_stub(),
            schemas=_build_schemas_stub(),
            logger=_LoggerStub(),
        )
        return service, crud_produtos

    @pytest.mark.asyncio
    async def test_generation_task_service_marks_success_for_titulo():
        """Run test generation task service marks success for titulo in this workflow."""
        produto = _ProdutoStub()
        service, crud_produtos = _build_service(produto=produto)
    
        async def _fake_generation(**kwargs):
            """Run fake generation in this workflow."""
            return ["Titulo 1", "Titulo 2"]
    
        await service.run_generation_task(
            user_id=1,
            produto_id=10,
            tipo_geracao_principal="titulo",
            funcao_geracao_ia_no_servico=_fake_generation,
        )
    
        assert produto.status_titulo_ia == "CONCLUIDO"
        assert produto.titulos_sugeridos == ["Titulo 1", "Titulo 2"]
        assert produto.dados_brutos_web["titulos_sugeridos_gerados"] == ["Titulo 1", "Titulo 2"]
        assert len(crud_produtos.updates) >= 2

    @pytest.mark.asyncio
    async def test_generation_task_service_marks_failure_for_empty_result():
        """Run test generation task service marks failure for empty result in this workflow."""
        produto = _ProdutoStub()
        service, crud_produtos = _build_service(produto=produto)
    
        async def _fake_generation(**kwargs):
            """Run fake generation in this workflow."""
            return ""
    
        await service.run_generation_task(
            user_id=1,
            produto_id=10,
            tipo_geracao_principal="descricao",
            funcao_geracao_ia_no_servico=_fake_generation,
        )
     
        assert produto.status_descricao_ia == "FALHA"

    @pytest.mark.asyncio
    async def test_generation_task_service_persists_description_in_raw_data():
        """Run test generation task service persists description in raw data in this workflow."""
        produto = _ProdutoStub()
        service, _crud_produtos = _build_service(produto=produto)

        async def _fake_generation(**kwargs):
            """Run fake generation in this workflow."""
            return "Descricao consolidada da peca para vitrine."

        await service.run_generation_task(
            user_id=1,
            produto_id=10,
            tipo_geracao_principal="descricao",
            funcao_geracao_ia_no_servico=_fake_generation,
        )

        assert produto.status_descricao_ia == "CONCLUIDO"
        assert (
            produto.dados_brutos_web["descricao_gerada"]
            == "Descricao consolidada da peca para vitrine."
        )

    @pytest.mark.asyncio
    async def test_generation_task_service_description_does_not_change_titles():
        """Ensure descricao workflow does not overwrite title artifacts."""
        produto = _ProdutoStub()
        produto.titulos_sugeridos = ["Titulo legado"]
        produto.status_titulo_ia = "CONCLUIDO"
        service, _crud_produtos = _build_service(produto=produto)

        async def _fake_generation(**kwargs):
            """Run fake generation in this workflow."""
            return "Descricao nova e objetiva."

        await service.run_generation_task(
            user_id=1,
            produto_id=10,
            tipo_geracao_principal="descricao",
            funcao_geracao_ia_no_servico=_fake_generation,
        )

        assert produto.status_descricao_ia == "CONCLUIDO"
        assert produto.descricao_chat_api == "Descricao nova e objetiva."
        assert produto.titulos_sugeridos == ["Titulo legado"]
        assert produto.status_titulo_ia == "CONCLUIDO"

    @pytest.mark.asyncio
    async def test_generation_task_service_titles_do_not_change_description():
        """Ensure titulo workflow does not overwrite description artifacts."""
        produto = _ProdutoStub()
        produto.descricao_chat_api = "Descricao legada"
        produto.status_descricao_ia = "CONCLUIDO"
        service, _crud_produtos = _build_service(produto=produto)

        async def _fake_generation(**kwargs):
            """Run fake generation in this workflow."""
            return ["Titulo novo 1", "Titulo novo 2"]

        await service.run_generation_task(
            user_id=1,
            produto_id=10,
            tipo_geracao_principal="titulo",
            funcao_geracao_ia_no_servico=_fake_generation,
        )

        assert produto.status_titulo_ia == "CONCLUIDO"
        assert produto.titulos_sugeridos == ["Titulo novo 1", "Titulo novo 2"]
        assert produto.descricao_chat_api == "Descricao legada"
        assert produto.status_descricao_ia == "CONCLUIDO"

_db_session_factory = _TopLevelFunctionSurface._db_session_factory
_build_models_stub = _TopLevelFunctionSurface._build_models_stub
_build_schemas_stub = _TopLevelFunctionSurface._build_schemas_stub
_build_service = _TopLevelFunctionSurface._build_service
test_generation_task_service_marks_success_for_titulo = _TopLevelFunctionSurface.test_generation_task_service_marks_success_for_titulo
test_generation_task_service_marks_failure_for_empty_result = _TopLevelFunctionSurface.test_generation_task_service_marks_failure_for_empty_result
test_generation_task_service_persists_description_in_raw_data = _TopLevelFunctionSurface.test_generation_task_service_persists_description_in_raw_data
test_generation_task_service_description_does_not_change_titles = _TopLevelFunctionSurface.test_generation_task_service_description_does_not_change_titles
test_generation_task_service_titles_do_not_change_description = _TopLevelFunctionSurface.test_generation_task_service_titles_do_not_change_description






class _LoggerStub:
    """Represent logger stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.logs = []

    def info(self, *args, **kwargs):
        """Run info in this workflow."""
        self.logs.append(("info", args, kwargs))

    def warning(self, *args, **kwargs):
        """Run warning in this workflow."""
        self.logs.append(("warning", args, kwargs))

    def error(self, *args, **kwargs):
        """Run error in this workflow."""
        self.logs.append(("error", args, kwargs))

    def exception(self, *args, **kwargs):
        """Run exception in this workflow."""
        self.logs.append(("exception", args, kwargs))






