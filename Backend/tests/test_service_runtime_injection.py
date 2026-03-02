"""Module test service runtime injection.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend import models
from Backend import database as database_module
from Backend.create_tables import CreateTablesWorkflow
from Backend.infrastructure.repositories.fornecedor_import_job_repository import (
    FornecedorImportJobRepository,
)
from Backend.initial_data import InitialDataWorkflow
from Backend.testing.runtime_apis import (
    CatalogStorageWorkflow,
    LineMappingWorkflow,
    PdfJobWorkflow,
    TabularIngestionWorkflow,
    TabularPreviewWorkflow,
    WebExtractionEnrichmentWorkflow,
)
from Backend.tasks import TaskWorkflow


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_create_tables_workflow_delega_runtime_injetado():
        """Execute test_create_tables_workflow_delega_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        called = []
    
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def create_all_tables(self):
                """Execute create_all_tables.

                This callable is documented to make behavior explicit for readers.
                """
                called.append("ok")
    
        workflow = CreateTablesWorkflow(runtime=FakeRuntime())
        workflow.create_all_tables()
    
        assert called == ["ok"]

    def test_database_get_db_yields_session_and_closes(monkeypatch):
        """Execute test_database_get_db_yields_session_and_closes.

        This callable is documented to make behavior explicit for readers.
        """
        called = []

        class FakeSession:
            """Class FakeSession.

            Encapsulates one responsibility in the backend architecture.
            """
            def close(self):
                """Execute close.

                This callable is documented to make behavior explicit for readers.
                """
                called.append("close")

        def fake_session_local():
            """Execute fake_session_local.

            This callable is documented to make behavior explicit for readers.
            """
            called.append("create")
            return FakeSession()

        monkeypatch.setattr(database_module, "SessionLocal", fake_session_local)
        sessions = list(database_module.get_db())

        assert len(sessions) == 1
        assert called == ["create", "close"]

    def test_task_workflow_delega_runtime_injetado():
        """Execute test_task_workflow_delega_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        called = []
    
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def process_pdf_extraction_task(self, *, import_job_id, page_number, db_url):
                """Execute process_pdf_extraction_task.

                This callable is documented to make behavior explicit for readers.
                """
                called.append((import_job_id, page_number, db_url))
    
        workflow = TaskWorkflow(runtime=FakeRuntime())
        workflow.process_pdf_extraction_task(import_job_id=10, page_number=2, db_url="db-url")
    
        assert called == [(10, 2, "db-url")]

    def test_line_mapping_workflow_delega_runtime_injetado():
        """Execute test_line_mapping_workflow_delega_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def processar_linha_padronizada(self, *, linha_original, mapeamento_colunas_usuario=None):
                """Execute processar_linha_padronizada.

                This callable is documented to make behavior explicit for readers.
                """
                return {
                    "nome_base": linha_original.get("nome"),
                    "mapping": mapeamento_colunas_usuario,
                }
    
        workflow = LineMappingWorkflow(runtime=FakeRuntime())
        result = workflow.processar_linha_padronizada(
            {"nome": "Produto X"},
            {"nome": "nome_base"},
        )
    
        assert result == {"nome_base": "Produto X", "mapping": {"nome": "nome_base"}}

    @pytest.mark.asyncio
    async def test_user_and_job_components_operam_com_dependencias_injetadas():
        """Execute test_user_and_job_components_operam_com_dependencias_injetadas.

        This callable is documented to make behavior explicit for readers.
        """
        class UserRuntime:
            """Class UserRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def get_user(self, **kwargs):
                """Execute get_user.

                This callable is documented to make behavior explicit for readers.
                """
                return {"workflow": "user", **kwargs}

        class InitialDataRuntime:
            """Class InitialDataRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def create_initial_data(self, **kwargs):
                """Execute create_initial_data.

                This callable is documented to make behavior explicit for readers.
                """
                return {"workflow": "initial_data", **kwargs}
    
        class UserWorkflow:
            """Class UserWorkflow.

            Encapsulates one responsibility in the backend architecture.
            """
            def __init__(self, runtime):
                """Execute __init__.

                This callable is documented to make behavior explicit for readers.
                """
                self._runtime = runtime

            def get_user(self, db, user_id):
                """Execute get_user.

                This callable is documented to make behavior explicit for readers.
                """
                return self._runtime.get_user(db=db, user_id=user_id)

        class _FakeDb:
            """Class _FakeDb.

            Encapsulates one responsibility in the backend architecture.
            """
            def __init__(self):
                """Execute __init__.

                This callable is documented to make behavior explicit for readers.
                """
                self.added = []
                self.commits = 0
                self.refreshed = []

            def add(self, obj):
                """Execute add.

                This callable is documented to make behavior explicit for readers.
                """
                self.added.append(obj)

            def commit(self):
                """Execute commit.

                This callable is documented to make behavior explicit for readers.
                """
                self.commits += 1

            def refresh(self, obj):
                """Execute refresh.

                This callable is documented to make behavior explicit for readers.
                """
                self.refreshed.append(obj)

        user_workflow = UserWorkflow(runtime=UserRuntime())
        job_workflow = FornecedorImportJobRepository(_FakeDb())
        initial_data_workflow = InitialDataWorkflow(runtime=InitialDataRuntime())

        user = user_workflow.get_user(db="db", user_id=3)
        job = job_workflow.update_job_status(job=SimpleNamespace(status="PENDING"), status="DONE")
        initial = initial_data_workflow.create_initial_data(session="db")

        assert user["workflow"] == "user"
        assert job.status == "DONE"
        assert initial["workflow"] == "initial_data"

    @pytest.mark.asyncio
    async def test_catalog_storage_workflow_delega_runtime_injetado():
        """Execute test_catalog_storage_workflow_delega_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        called = []
    
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def save_uploaded_catalog(self, *, file, fornecedor_id=None):
                """Execute save_uploaded_catalog.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("save", file, fornecedor_id))
                return {"stored_filename": "arquivo.pdf"}
    
            def delete_catalog_file(self, *, stored_filename):
                """Execute delete_catalog_file.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("delete", stored_filename))
    
            def get_file_path_by_id(self, *, db, file_id):
                """Execute get_file_path_by_id.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("path", db, file_id))
                return f"/tmp/{file_id}"
    
        workflow = CatalogStorageWorkflow(runtime=FakeRuntime())
        saved = await workflow.save_uploaded_catalog(file="conteudo", fornecedor_id=5)
        workflow.delete_catalog_file("arquivo.pdf")
        path = workflow.get_file_path_by_id(db="db", file_id="11")
    
        assert saved == {"stored_filename": "arquivo.pdf"}
        assert path == "/tmp/11"
        assert called == [
            ("save", "conteudo", 5),
            ("delete", "arquivo.pdf"),
            ("path", "db", "11"),
        ]

    @pytest.mark.asyncio
    async def test_tabular_workflows_delegam_runtime_injetado():
        """Execute test_tabular_workflows_delegam_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeIngestionRuntime:
            """Class FakeIngestionRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def processar_arquivo_excel(self, **kwargs):
                """Execute processar_arquivo_excel.

                This callable is documented to make behavior explicit for readers.
                """
                return [{"from": "excel", **kwargs}]
    
            async def processar_arquivo_csv(self, **kwargs):
                """Execute processar_arquivo_csv.

                This callable is documented to make behavior explicit for readers.
                """
                return [{"from": "csv", **kwargs}]
    
        class FakePreviewRuntime:
            """Class FakePreviewRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def preview_arquivo_excel(self, **kwargs):
                """Execute preview_arquivo_excel.

                This callable is documented to make behavior explicit for readers.
                """
                return {"preview": "excel", **kwargs}
    
            async def preview_arquivo_csv(self, **kwargs):
                """Execute preview_arquivo_csv.

                This callable is documented to make behavior explicit for readers.
                """
                return {"preview": "csv", **kwargs}
    
        ingestion = TabularIngestionWorkflow(runtime=FakeIngestionRuntime())
        preview = TabularPreviewWorkflow(runtime=FakePreviewRuntime())
    
        excel_rows = await ingestion.processar_arquivo_excel(
            conteudo_arquivo=b"abc",
            mapeamento_colunas_usuario={"a": "b"},
            sheet_name="Plan1",
            product_type_id=1,
        )
        csv_rows = await ingestion.processar_arquivo_csv(
            conteudo_arquivo=b"def",
            mapeamento_colunas_usuario={"c": "d"},
            product_type_id=2,
        )
        excel_preview = await preview.preview_arquivo_excel(conteudo_arquivo=b"x", max_rows=3)
        csv_preview = await preview.preview_arquivo_csv(conteudo_arquivo=b"y", max_rows=4)
    
        assert excel_rows[0]["from"] == "excel"
        assert csv_rows[0]["from"] == "csv"
        assert excel_preview["preview"] == "excel"
        assert csv_preview["preview"] == "csv"

    @pytest.mark.asyncio
    async def test_pdf_job_workflow_delega_runtime_injetado():
        """Execute test_pdf_job_workflow_delega_runtime_injetado.

        This callable is documented to make behavior explicit for readers.
        """
        called = []
    
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def process_pdf_job(self, **kwargs):
                """Execute process_pdf_job.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("process", kwargs))
    
            def extract_data_from_single_page(self, **kwargs):
                """Execute extract_data_from_single_page.

                This callable is documented to make behavior explicit for readers.
                """
                called.append(("single", kwargs))
                return {"ok": True, "page": kwargs["page_number"]}
    
        workflow = PdfJobWorkflow(runtime=FakeRuntime())
        await workflow.process_pdf_job(job_id=9, pdf_path="c:/tmp/a.pdf", start_page=4, mapping={"a": "b"})
        data = workflow.extract_data_from_single_page(file_path="c:/tmp/a.pdf", page_number=8)
    
        assert data == {"ok": True, "page": 8}
        assert called[0][0] == "process"
        assert called[1][0] == "single"

    @pytest.mark.asyncio
    async def test_web_extraction_workflow_usa_runtime_injetado_para_timestamp_e_html():
        """Execute test_web_extraction_workflow_usa_runtime_injetado_para_timestamp_e_html.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def now_iso(self) -> str:
                """Execute now_iso.

                This callable is documented to make behavior explicit for readers.
                """
                return "2026-02-01T12:00:00+00:00"
    
            async def collect_html(self, *, url: str):
                """Execute collect_html.

                This callable is documented to make behavior explicit for readers.
                """
                assert url == "https://example.com/produto"
                return "<html>ok</html>"
    
            def extract_main_text(self, *, html_content: str):
                """Execute extract_main_text.

                This callable is documented to make behavior explicit for readers.
                """
                return "texto"
    
            def extract_structured_metadata(self, *, html_content: str, url: str):
                """Execute extract_structured_metadata.

                This callable is documented to make behavior explicit for readers.
                """
                return {}
    
            def normalize_metadata(self, *, metadata):
                """Execute normalize_metadata.

                This callable is documented to make behavior explicit for readers.
                """
                return {}
    
        class FakeDb:
            """Class FakeDb.

            Encapsulates one responsibility in the backend architecture.
            """
            def __init__(self):
                """Execute __init__.

                This callable is documented to make behavior explicit for readers.
                """
                self.commits = 0
    
            def add(self, _obj):
                """Execute add.

                This callable is documented to make behavior explicit for readers.
                """
                return None
    
            def commit(self):
                """Execute commit.

                This callable is documented to make behavior explicit for readers.
                """
                self.commits += 1
    
            def refresh(self, _obj, attribute_names=None):
                """Execute refresh.

                This callable is documented to make behavior explicit for readers.
                """
                return None
    
        produto = SimpleNamespace(
            id=123,
            status_enriquecimento_web=None,
            dados_brutos_web={},
            log_enriquecimento_web=None,
            fornecedor=None,
        )
        db = FakeDb()
        workflow = WebExtractionEnrichmentWorkflow(
            db=db,
            url="https://example.com/produto",
            produto=produto,
            runtime=FakeRuntime(),
        )
    
        html = await workflow._collect_html()
    
        assert html == "<html>ok</html>"
        assert workflow.log_enriquecimento[0]["timestamp"] == "2026-02-01T12:00:00+00:00"
        assert produto.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO
        assert db.commits == 1

test_create_tables_workflow_delega_runtime_injetado = _TopLevelFunctionSurface.test_create_tables_workflow_delega_runtime_injetado
test_database_get_db_yields_session_and_closes = _TopLevelFunctionSurface.test_database_get_db_yields_session_and_closes
test_task_workflow_delega_runtime_injetado = _TopLevelFunctionSurface.test_task_workflow_delega_runtime_injetado
test_line_mapping_workflow_delega_runtime_injetado = _TopLevelFunctionSurface.test_line_mapping_workflow_delega_runtime_injetado
test_user_and_job_components_operam_com_dependencias_injetadas = _TopLevelFunctionSurface.test_user_and_job_components_operam_com_dependencias_injetadas
test_catalog_storage_workflow_delega_runtime_injetado = _TopLevelFunctionSurface.test_catalog_storage_workflow_delega_runtime_injetado
test_tabular_workflows_delegam_runtime_injetado = _TopLevelFunctionSurface.test_tabular_workflows_delegam_runtime_injetado
test_pdf_job_workflow_delega_runtime_injetado = _TopLevelFunctionSurface.test_pdf_job_workflow_delega_runtime_injetado
test_web_extraction_workflow_usa_runtime_injetado_para_timestamp_e_html = _TopLevelFunctionSurface.test_web_extraction_workflow_usa_runtime_injetado_para_timestamp_e_html


















