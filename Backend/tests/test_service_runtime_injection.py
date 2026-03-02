"""Module test service runtime injection.

Contains backend logic related to test service runtime injection and documents its role in the OOP architecture.
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

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_create_tables_workflow_delega_runtime_injetado():
        """Run test create tables workflow delega runtime injetado in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def create_all_tables(self):
                """Create all tables for this workflow."""
                called.append("ok")
    
        workflow = CreateTablesWorkflow(runtime=FakeRuntime())
        workflow.create_all_tables()
    
        assert called == ["ok"]

    def test_database_get_db_yields_session_and_closes(monkeypatch):
        """Run test database get db yields session and closes in this workflow."""
        called = []

        class FakeSession:
            """Represent fake session and centralize responsibilities for this module."""
            def close(self):
                """Run close in this workflow."""
                called.append("close")

        def fake_session_local():
            """Run fake session local in this workflow."""
            called.append("create")
            return FakeSession()

        monkeypatch.setattr(database_module, "SessionLocal", fake_session_local)
        sessions = list(database_module.get_db())

        assert len(sessions) == 1
        assert called == ["create", "close"]

    def test_task_workflow_delega_runtime_injetado():
        """Run test task workflow delega runtime injetado in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def process_pdf_extraction_task(self, *, import_job_id, page_number):
                """Process pdf extraction task for this workflow."""
                called.append((import_job_id, page_number))
    
        workflow = TaskWorkflow(runtime=FakeRuntime())
        workflow.process_pdf_extraction_task(import_job_id=10, page_number=2)
    
        assert called == [(10, 2)]

    def test_line_mapping_workflow_delega_runtime_injetado():
        """Run test line mapping workflow delega runtime injetado in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def processar_linha_padronizada(self, *, linha_original, mapeamento_colunas_usuario=None):
                """Run processar linha padronizada in this workflow."""
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
        """Run test user and job components operam com dependencias injetadas in this workflow."""
        class UserRuntime:
            """Represent user runtime and centralize responsibilities for this module."""
            def get_user(self, **kwargs):
                """Return user for this workflow."""
                return {"workflow": "user", **kwargs}

        class InitialDataRuntime:
            """Represent initial data runtime and centralize responsibilities for this module."""
            def create_initial_data(self, **kwargs):
                """Create initial data for this workflow."""
                return {"workflow": "initial_data", **kwargs}
    
        class UserWorkflow:
            """Represent user workflow and centralize responsibilities for this module."""
            def __init__(self, runtime):
                """Initialize collaborators and configuration required by this component."""
                self._runtime = runtime

            def get_user(self, db, user_id):
                """Return user for this workflow."""
                return self._runtime.get_user(db=db, user_id=user_id)

        class _FakeDb:
            """Represent fake db and centralize responsibilities for this module."""
            def __init__(self):
                """Initialize collaborators and configuration required by this component."""
                self.added = []
                self.commits = 0
                self.refreshed = []

            def add(self, obj):
                """Run add in this workflow."""
                self.added.append(obj)

            def commit(self):
                """Run commit in this workflow."""
                self.commits += 1

            def refresh(self, obj):
                """Run refresh in this workflow."""
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
        """Run test catalog storage workflow delega runtime injetado in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            async def save_uploaded_catalog(self, *, file, fornecedor_id=None):
                """Run save uploaded catalog in this workflow."""
                called.append(("save", file, fornecedor_id))
                return {"stored_filename": "arquivo.pdf"}
    
            def delete_catalog_file(self, *, stored_filename):
                """Delete catalog file for this workflow."""
                called.append(("delete", stored_filename))
    
            def get_file_path_by_id(self, *, db, file_id):
                """Return file path by id for this workflow."""
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
        """Run test tabular workflows delegam runtime injetado in this workflow."""
        class FakeIngestionRuntime:
            """Represent fake ingestion runtime and centralize responsibilities for this module."""
            async def processar_arquivo_excel(self, **kwargs):
                """Run processar arquivo excel in this workflow."""
                return [{"from": "excel", **kwargs}]
    
            async def processar_arquivo_csv(self, **kwargs):
                """Run processar arquivo csv in this workflow."""
                return [{"from": "csv", **kwargs}]
    
        class FakePreviewRuntime:
            """Represent fake preview runtime and centralize responsibilities for this module."""
            async def preview_arquivo_excel(self, **kwargs):
                """Run preview arquivo excel in this workflow."""
                return {"preview": "excel", **kwargs}
    
            async def preview_arquivo_csv(self, **kwargs):
                """Run preview arquivo csv in this workflow."""
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
        """Run test pdf job workflow delega runtime injetado in this workflow."""
        called = []
    
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            async def process_pdf_job(self, **kwargs):
                """Process pdf job for this workflow."""
                called.append(("process", kwargs))
    
            def extract_data_from_single_page(self, **kwargs):
                """Extract data from single page for this workflow."""
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
        """Run test web extraction workflow usa runtime injetado para timestamp e html in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def now_iso(self) -> str:
                """Run now iso in this workflow."""
                return "2026-02-01T12:00:00+00:00"
    
            async def collect_html(self, *, url: str):
                """Run collect html in this workflow."""
                assert url == "https://example.com/produto"
                return "<html>ok</html>"
    
            def extract_main_text(self, *, html_content: str):
                """Extract main text for this workflow."""
                return "texto"
    
            def extract_structured_metadata(self, *, html_content: str, url: str):
                """Extract structured metadata for this workflow."""
                return {}
    
            def normalize_metadata(self, *, metadata):
                """Normalize metadata for this workflow."""
                return {}
    
        class FakeDb:
            """Represent fake db and centralize responsibilities for this module."""
            def __init__(self):
                """Initialize collaborators and configuration required by this component."""
                self.commits = 0
    
            def add(self, _obj):
                """Run add in this workflow."""
                return None
    
            def commit(self):
                """Run commit in this workflow."""
                self.commits += 1
    
            def refresh(self, _obj, attribute_names=None):
                """Run refresh in this workflow."""
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


















