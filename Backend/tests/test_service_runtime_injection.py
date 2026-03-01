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

    def test_create_tables_workflow_delega_runtime_injetado():
        called = []
    
        class FakeRuntime:
            def create_all_tables(self):
                called.append("ok")
    
        workflow = CreateTablesWorkflow(runtime=FakeRuntime())
        workflow.create_all_tables()
    
        assert called == ["ok"]

    def test_database_get_db_yields_session_and_closes(monkeypatch):
        called = []

        class FakeSession:
            def close(self):
                called.append("close")

        def fake_session_local():
            called.append("create")
            return FakeSession()

        monkeypatch.setattr(database_module, "SessionLocal", fake_session_local)
        sessions = list(database_module.get_db())

        assert len(sessions) == 1
        assert called == ["create", "close"]

    def test_task_workflow_delega_runtime_injetado():
        called = []
    
        class FakeRuntime:
            def process_pdf_extraction_task(self, *, import_job_id, page_number, db_url):
                called.append((import_job_id, page_number, db_url))
    
        workflow = TaskWorkflow(runtime=FakeRuntime())
        workflow.process_pdf_extraction_task(import_job_id=10, page_number=2, db_url="db-url")
    
        assert called == [(10, 2, "db-url")]

    def test_line_mapping_workflow_delega_runtime_injetado():
        class FakeRuntime:
            def processar_linha_padronizada(self, *, linha_original, mapeamento_colunas_usuario=None):
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
        class UserRuntime:
            def get_user(self, **kwargs):
                return {"workflow": "user", **kwargs}

        class InitialDataRuntime:
            def create_initial_data(self, **kwargs):
                return {"workflow": "initial_data", **kwargs}
    
        class UserWorkflow:
            def __init__(self, runtime):
                self._runtime = runtime

            def get_user(self, db, user_id):
                return self._runtime.get_user(db=db, user_id=user_id)

        class _FakeDb:
            def __init__(self):
                self.added = []
                self.commits = 0
                self.refreshed = []

            def add(self, obj):
                self.added.append(obj)

            def commit(self):
                self.commits += 1

            def refresh(self, obj):
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
        called = []
    
        class FakeRuntime:
            async def save_uploaded_catalog(self, *, file, fornecedor_id=None):
                called.append(("save", file, fornecedor_id))
                return {"stored_filename": "arquivo.pdf"}
    
            def delete_catalog_file(self, *, stored_filename):
                called.append(("delete", stored_filename))
    
            def get_file_path_by_id(self, *, db, file_id):
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
        class FakeIngestionRuntime:
            async def processar_arquivo_excel(self, **kwargs):
                return [{"from": "excel", **kwargs}]
    
            async def processar_arquivo_csv(self, **kwargs):
                return [{"from": "csv", **kwargs}]
    
        class FakePreviewRuntime:
            async def preview_arquivo_excel(self, **kwargs):
                return {"preview": "excel", **kwargs}
    
            async def preview_arquivo_csv(self, **kwargs):
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
        called = []
    
        class FakeRuntime:
            async def process_pdf_job(self, **kwargs):
                called.append(("process", kwargs))
    
            def extract_data_from_single_page(self, **kwargs):
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
        class FakeRuntime:
            def now_iso(self) -> str:
                return "2026-02-01T12:00:00+00:00"
    
            async def collect_html(self, *, url: str):
                assert url == "https://example.com/produto"
                return "<html>ok</html>"
    
            def extract_main_text(self, *, html_content: str):
                return "texto"
    
            def extract_structured_metadata(self, *, html_content: str, url: str):
                return {}
    
            def normalize_metadata(self, *, metadata):
                return {}
    
        class FakeDb:
            def __init__(self):
                self.commits = 0
    
            def add(self, _obj):
                return None
    
            def commit(self):
                self.commits += 1
    
            def refresh(self, _obj, attribute_names=None):
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


















