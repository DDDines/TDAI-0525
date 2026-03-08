"""Low-hanging backend coverage for adapters, tasks and small runtimes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from Backend import schemas
from Backend.application.services.pdf_extraction_task_service import PdfExtractionTaskService
from Backend.core.api_key_validation import ApiKeyValidationRuntime
from Backend.create_tables import CreateTablesRuntime, CreateTablesWorkflow
from Backend.infrastructure.adapters.ia_generation_adapter import IAGenerationServiceAdapter
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)
from Backend.tasks import TaskRuntime, TaskWorkflow


class _FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeSessionProvider:
    def __init__(self, session):
        self._session = session

    def open_session(self):
        return self._session


class _FakeCatalogImportFileRepo:
    def __init__(self, job=None):
        self.job = job
        self.updated_jobs = []

    def get_catalog_file(self, *, file_id):
        _ = file_id
        return self.job

    def update_catalog_file(self, *, catalog_file):
        self.updated_jobs.append(catalog_file)
        return catalog_file


def test_api_key_validation_runtime_normalizes_and_validates():
    assert ApiKeyValidationRuntime.normalize_optional_secret(None) is None
    assert ApiKeyValidationRuntime.normalize_optional_secret("  abc  ") == "abc"
    assert ApiKeyValidationRuntime.looks_like_openai_api_key(None) is False
    assert ApiKeyValidationRuntime.looks_like_openai_api_key("adminpassword") is False
    assert ApiKeyValidationRuntime.looks_like_openai_api_key("sk-short") is False
    assert ApiKeyValidationRuntime.looks_like_openai_api_key("sk-12345678901234567890") is True


def test_create_tables_workflow_delegates_to_runtime():
    called = []

    class FakeRuntime:
        def create_all_tables(self):
            called.append("create_all_tables")

    CreateTablesWorkflow(runtime=FakeRuntime()).create_all_tables()
    assert called == ["create_all_tables"]


def test_create_tables_runtime_creates_engine_and_tables(monkeypatch, capsys):
    called = []

    class FakeMetadata:
        def create_all(self, engine):
            called.append(("create_all", engine))

    monkeypatch.setattr("Backend.create_tables.settings", SimpleNamespace(DATABASE_URL="sqlite:///catalog.db"))
    monkeypatch.setattr("Backend.create_tables.Base", SimpleNamespace(metadata=FakeMetadata()))
    monkeypatch.setattr("Backend.create_tables.create_engine", lambda db_url: f"engine:{db_url}")

    CreateTablesRuntime().create_all_tables()

    output = capsys.readouterr().out
    assert ("create_all", "engine:sqlite:///catalog.db") in called
    assert "SUCESSO" in output


def test_create_tables_runtime_reports_error_without_raising(monkeypatch, capsys):
    monkeypatch.setattr("Backend.create_tables.settings", SimpleNamespace(DATABASE_URL="sqlite:///catalog.db"))

    def fail_create_engine(_db_url):
        raise RuntimeError("sem conexao")

    monkeypatch.setattr("Backend.create_tables.create_engine", fail_create_engine)

    CreateTablesRuntime().create_all_tables()

    output = capsys.readouterr().out
    assert "ERRO ao criar as tabelas" in output


@pytest.mark.asyncio
async def test_ia_generation_adapter_delegates_all_methods():
    called = []
    user = SimpleNamespace(id=7)
    session = "db"
    expected = schemas.SugestoesAtributosResponse(
        produto_id=10,
        sugestoes_atributos=[
            schemas.SugestaoAtributoItem(chave_atributo="material", valor_sugerido="aco")
        ],
        modelo_ia_utilizado="gemini",
    )

    class FakeRuntime:
        async def gerar_titulos_com_openai(self, **kwargs):
            called.append(("titulos_openai", kwargs))
            return ["t1"]

        async def gerar_descricao_com_openai(self, **kwargs):
            called.append(("descricao_openai", kwargs))
            return "descricao"

        async def gerar_titulos_com_gemini(self, **kwargs):
            called.append(("titulos_gemini", kwargs))
            return ["g1"]

        async def gerar_descricao_com_gemini(self, **kwargs):
            called.append(("descricao_gemini", kwargs))
            return "gemini"

        async def sugerir_valores_atributos_com_gemini(self, **kwargs):
            called.append(("atributos_gemini", kwargs))
            return expected

    adapter = IAGenerationServiceAdapter(runtime=FakeRuntime())

    assert await adapter.gerar_titulos_com_openai(session=session, produto_id=10, user=user) == ["t1"]
    assert await adapter.gerar_descricao_com_openai(session=session, produto_id=10, user=user) == "descricao"
    assert await adapter.gerar_titulos_com_gemini(session=session, produto_id=10, user=user) == ["g1"]
    assert await adapter.gerar_descricao_com_gemini(session=session, produto_id=10, user=user) == "gemini"
    assert (
        await adapter.sugerir_valores_atributos_com_gemini(
            session=session,
            produto_id=10,
            user=user,
        )
        == expected
    )
    assert called[0][1]["db"] == session
    assert called[-1][1]["produto_id"] == 10


@pytest.mark.asyncio
async def test_web_data_extractor_adapter_delegates_all_methods():
    called = []
    produto = SimpleNamespace(id=5)
    user = SimpleNamespace(id=7)

    class FakeRuntime:
        def busca_publica_disponivel(self):
            called.append(("busca_publica_disponivel", {}))
            return True

        async def buscar_urls_publicas(self, **kwargs):
            called.append(("buscar_urls_publicas", kwargs))
            return ["https://a"]

        async def buscar_urls_google(self, **kwargs):
            called.append(("buscar_urls_google", kwargs))
            return ["https://b"]

        async def coletar_conteudo_pagina_playwright(self, **kwargs):
            called.append(("coletar_conteudo_pagina_playwright", kwargs))
            return "<html />"

        def extrair_texto_principal_com_trafilatura(self, **kwargs):
            called.append(("extrair_texto_principal_com_trafilatura", kwargs))
            return "texto"

        def extrair_metadados_estruturados(self, **kwargs):
            called.append(("extrair_metadados_estruturados", kwargs))
            return {"title": "produto"}

        def normalizar_dados_de_metadados(self, **kwargs):
            called.append(("normalizar_dados_de_metadados", kwargs))
            return {"title": "produto"}

        async def extrair_dados_produto_com_llm(self, **kwargs):
            called.append(("extrair_dados_produto_com_llm", kwargs))
            return {"nome": "produto"}

        async def extract_relevant_data_from_url(self, **kwargs):
            called.append(("extract_relevant_data_from_url", kwargs))
            return produto

        def extract_text_from_image_region(self, **kwargs):
            called.append(("extract_text_from_image_region", kwargs))
            return "ocr"

    adapter = WebDataExtractorServiceAdapter(runtime=FakeRuntime())

    assert adapter.busca_publica_disponivel() is True
    assert await adapter.buscar_urls_publicas("produto", num_results=2) == ["https://a"]
    assert await adapter.buscar_urls_google("produto", num_results=2) == ["https://b"]
    assert await adapter.coletar_conteudo_pagina_playwright("https://a") == "<html />"
    assert adapter.extrair_texto_principal_com_trafilatura("<html />") == "texto"
    assert adapter.extrair_metadados_estruturados("<html />", "https://a") == {"title": "produto"}
    assert adapter.normalizar_dados_de_metadados({"title": "produto"}) == {"title": "produto"}
    assert (
        await adapter.extrair_dados_produto_com_llm(
            "texto",
            metadados_normalizados={"title": "produto"},
            campos_desejados=["nome"],
            produto_nome_base="Base",
            user=user,
        )
        == {"nome": "produto"}
    )
    assert (
        await adapter.extract_relevant_data_from_url(
            session="db",
            url="https://a",
            produto=produto,
        )
        is produto
    )
    assert adapter.extract_text_from_image_region(b"123") == "ocr"
    assert called[-1] == ("extract_text_from_image_region", {"image_bytes": b"123"})


def test_task_workflow_and_runtime_delegate(monkeypatch):
    called = []

    class FakeRuntime:
        def process_pdf_extraction_task(self, **kwargs):
            called.append(("workflow", kwargs))

    TaskWorkflow(runtime=FakeRuntime()).process_pdf_extraction_task(import_job_id=3, page_number=9)

    class FakeTaskService:
        def process_pdf_extraction_task(self, **kwargs):
            called.append(("runtime", kwargs))

    runtime = TaskRuntime(task_service=FakeTaskService())
    runtime.process_pdf_extraction_task(import_job_id=4, page_number=10)

    monkeypatch.setattr(
        "Backend.tasks.ServiceContainerDependencySupport.get_background_session_provider",
        lambda: "session_provider",
    )
    monkeypatch.setattr(
        "Backend.tasks.ServiceContainer",
        lambda: SimpleNamespace(file_processing="file_processing_service"),
    )

    default_runtime = TaskRuntime()
    assert default_runtime._task_service._session_provider == "session_provider"
    assert default_runtime._task_service._file_processing_service == "file_processing_service"
    assert called == [
        ("workflow", {"import_job_id": 3, "page_number": 9}),
        ("runtime", {"import_job_id": 4, "page_number": 10}),
    ]


def test_pdf_extraction_task_service_resolves_absolute_and_relative_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "Backend.application.services.pdf_extraction_task_service.settings",
        SimpleNamespace(UPLOAD_DIRECTORY=str(tmp_path)),
    )
    service = PdfExtractionTaskService(
        session_provider=_FakeSessionProvider(_FakeSession()),
        file_processing_service=SimpleNamespace(),
    )

    absolute = service._resolve_catalog_file_path("arquivo.pdf")
    assert absolute == tmp_path / "catalogs" / "arquivo.pdf"

    monkeypatch.setattr(
        "Backend.application.services.pdf_extraction_task_service.settings",
        SimpleNamespace(UPLOAD_DIRECTORY="uploads"),
    )
    relative = service._resolve_catalog_file_path("arquivo.pdf")
    assert relative.as_posix().endswith("static/uploads/catalogs/arquivo.pdf")


def test_pdf_extraction_task_service_returns_when_job_not_found(caplog):
    session = _FakeSession()
    repo = _FakeCatalogImportFileRepo(job=None)
    service = PdfExtractionTaskService(
        session_provider=_FakeSessionProvider(session),
        catalog_import_file_repository_factory=lambda _session: repo,
        file_processing_service=SimpleNamespace(),
    )

    service.process_pdf_extraction_task(import_job_id=1, page_number=2)

    assert "not found" in caplog.text.lower()
    assert session.closed is True
    assert repo.updated_jobs == []


def test_pdf_extraction_task_service_processes_successfully(tmp_path, monkeypatch):
    session = _FakeSession()
    catalogs_dir = tmp_path / "catalogs"
    catalogs_dir.mkdir()
    pdf_path = catalogs_dir / "catalog.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    monkeypatch.setattr(
        "Backend.application.services.pdf_extraction_task_service.settings",
        SimpleNamespace(UPLOAD_DIRECTORY=str(tmp_path)),
    )
    job = SimpleNamespace(stored_filename="catalog.pdf", status=None, resultado_json=None)
    repo = _FakeCatalogImportFileRepo(job=job)

    class FakeFileProcessingService:
        def extract_data_from_single_page(self, file_path, page_number):
            assert file_path == str(pdf_path)
            assert page_number == 4
            return {"page": page_number}

    service = PdfExtractionTaskService(
        session_provider=_FakeSessionProvider(session),
        catalog_import_file_repository_factory=lambda _session: repo,
        file_processing_service=FakeFileProcessingService(),
    )

    service.process_pdf_extraction_task(import_job_id=7, page_number=4)

    assert job.status == "COMPLETED"
    assert job.resultado_json == {"page": 4}
    assert len(repo.updated_jobs) == 2
    assert session.closed is True


def test_pdf_extraction_task_service_marks_failed_on_missing_file(tmp_path):
    session = _FakeSession()
    job = SimpleNamespace(stored_filename="missing.pdf", status=None, resultado_json=None, result_summary=None)
    repo = _FakeCatalogImportFileRepo(job=job)
    service = PdfExtractionTaskService(
        session_provider=_FakeSessionProvider(session),
        catalog_import_file_repository_factory=lambda _session: repo,
        file_processing_service=SimpleNamespace(),
    )

    service.process_pdf_extraction_task(import_job_id=8, page_number=1)

    assert job.status == "FAILED"
    assert "missing.pdf" in job.result_summary["error"]
    assert session.closed is True


def test_pdf_extraction_task_service_marks_failed_on_processing_error(tmp_path, monkeypatch):
    session = _FakeSession()
    catalogs_dir = tmp_path / "catalogs"
    catalogs_dir.mkdir()
    pdf_path = catalogs_dir / "catalog.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    monkeypatch.setattr(
        "Backend.application.services.pdf_extraction_task_service.settings",
        SimpleNamespace(UPLOAD_DIRECTORY=str(tmp_path)),
    )
    job = SimpleNamespace(stored_filename="catalog.pdf", status=None, resultado_json=None, result_summary=None)
    repo = _FakeCatalogImportFileRepo(job=job)

    class FakeFileProcessingService:
        def extract_data_from_single_page(self, _file_path, _page_number):
            raise RuntimeError("falha na extracao")

    service = PdfExtractionTaskService(
        session_provider=_FakeSessionProvider(session),
        catalog_import_file_repository_factory=lambda _session: repo,
        file_processing_service=FakeFileProcessingService(),
    )

    service.process_pdf_extraction_task(import_job_id=9, page_number=2)

    assert job.status == "FAILED"
    assert job.result_summary == {"error": "falha na extracao"}
    assert session.closed is True
