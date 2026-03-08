"""Extra coverage for small repositories and validator service branches."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend import models, schemas
from Backend.application.services import validator_crew_service as validator_service_module
from Backend.infrastructure.repositories.fornecedor_import_job_repository import (
    FornecedorImportJobRepository,
)
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)


class _QueryStub:
    def __init__(self, *, first_result=None, all_result=None, scalar_result=None):
        self.filters = []
        self.first_result = first_result
        self.all_result = all_result or []
        self.scalar_result = scalar_result
        self.offset_value = None
        self.limit_value = None

    def filter(self, *args):
        self.filters.extend(args)
        return self

    def order_by(self, *_args):
        return self

    def offset(self, value):
        self.offset_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_result

    def scalar(self):
        return self.scalar_result


class _DbStub:
    def __init__(self, *, query_results=None, dialect_name="sqlite"):
        self.query_results = list(query_results or [])
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)

    def query(self, *_args):
        if not self.query_results:
            raise AssertionError("unexpected query call")
        return self.query_results.pop(0)


def test_registro_uso_repository_create_and_basic_queries():
    create_db = _DbStub()
    repo = RegistroUsoIARepository(create_db)
    registro_in = schemas.RegistroUsoIACreate(
        user_id=1,
        produto_id=2,
        tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        modelo_ia="gemini",
        creditos_consumidos=1,
    )
    created = repo.create_registro_uso_ia(registro_in)
    assert create_db.added[0] is created
    assert create_db.commits == 1
    assert create_db.refreshed == [created]

    first_query = _QueryStub(first_result="registro")
    db = _DbStub(query_results=[first_query, _QueryStub(all_result=["uso"])])
    repo = RegistroUsoIARepository(db)
    assert repo.get_registro_uso_ia(registro_id=5) == "registro"
    assert repo.get_usos_ia_by_produto(produto_id=9, user_id=1, skip=2, limit=3) == ["uso"]
    assert db.query_results == []


def test_registro_uso_repository_filters_and_prefix_count_paths():
    with pytest.raises(ValueError):
        RegistroUsoIARepository._normalize_tipo_acao("tipo-invalido")
    assert (
        RegistroUsoIARepository._normalize_tipo_acao(models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO)
        == models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO
    )

    query_items = _QueryStub(all_result=["a", "b"])
    query_count = _QueryStub(scalar_result=4)
    db = _DbStub(query_results=[query_items, query_count], dialect_name="sqlite")
    repo = RegistroUsoIARepository(db)
    tipo = models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO

    rows = repo.get_registros_uso_ia(
        user_id=1,
        skip=3,
        limit=5,
        tipo_acao=tipo,
        data_inicio=SimpleNamespace(),
        data_fim=SimpleNamespace(),
    )
    total = repo.count_registros_uso_ia(
        user_id=1,
        tipo_acao=tipo,
        data_inicio=SimpleNamespace(),
        data_fim=SimpleNamespace(),
    )

    assert rows == ["a", "b"]
    assert total == 4
    assert query_items.offset_value == 3
    assert query_items.limit_value == 5
    assert len(query_items.filters) == 4
    assert len(query_count.filters) == 4

    sqlite_count = _QueryStub(scalar_result=2)
    postgres_count = _QueryStub(scalar_result=3)
    zero_count = _QueryStub(scalar_result=None)
    db_sqlite = _DbStub(query_results=[sqlite_count, zero_count], dialect_name="sqlite")
    db_postgres = _DbStub(query_results=[postgres_count], dialect_name="postgresql")

    sqlite_repo = RegistroUsoIARepository(db_sqlite)
    postgres_repo = RegistroUsoIARepository(db_postgres)

    assert (
        sqlite_repo.count_usos_ia_by_user_and_type_no_mes_corrente(
            user_id=1,
            tipo_geracao_prefix="titulo",
        )
        == 2
    )
    assert postgres_repo.count_usos_ia_by_user_and_type_no_mes_corrente(
        user_id=1,
        tipo_geracao_prefix="descricao",
    ) == 3
    assert sqlite_repo.get_geracoes_ia_count_no_mes_corrente(user_id=1) == 0

    unfiltered_items = _QueryStub(all_result=["x"])
    unfiltered_count = _QueryStub(scalar_result=1)
    unfiltered_db = _DbStub(query_results=[unfiltered_items, unfiltered_count], dialect_name="sqlite")
    unfiltered_repo = RegistroUsoIARepository(unfiltered_db)
    assert unfiltered_repo.get_registros_uso_ia(user_id=1) == ["x"]
    assert unfiltered_repo.count_registros_uso_ia(user_id=1) == 1


def test_fornecedor_import_job_repository_paths():
    create_db = _DbStub()
    repo = FornecedorImportJobRepository(create_db)
    created = repo.create_import_job(user_id=7)
    assert created.user_id == 7
    assert created.result_summary == {}
    assert create_db.commits == 1

    first_query = _QueryStub(first_result="job")
    update_db = _DbStub(query_results=[first_query])
    repo = FornecedorImportJobRepository(update_db)
    assert repo.get_import_job(job_id=9) == "job"

    job = SimpleNamespace(status="PENDING")
    updated = repo.update_job_status(job=job, status="DONE")
    assert updated.status == "DONE"
    assert update_db.added[-1] is job
    assert update_db.commits == 1


def test_validator_crew_service_startup_and_runtime_fallbacks(monkeypatch):
    warnings = []
    logger = SimpleNamespace(warning=lambda *args: warnings.append(args))

    class BrokenRunner:
        def __init__(self):
            raise RuntimeError("startup failed")

    monkeypatch.setattr(validator_service_module, "ValidatorCrewServiceAdapter", BrokenRunner)
    service = validator_service_module.ValidatorCrewService(logger=logger)
    assert service.run_validation_crew({"sku": "1"}) == {"sku": "1"}
    assert warnings

    class RuntimeBrokenRunner:
        def run_validation_crew(self, raw_data):
            _ = raw_data
            raise RuntimeError("runtime failed")

    warnings.clear()
    service = validator_service_module.ValidatorCrewService(
        logger=logger,
        runner=RuntimeBrokenRunner(),
    )
    assert service.run_validation_crew({"sku": "2"}) == {"sku": "2"}
    assert warnings
