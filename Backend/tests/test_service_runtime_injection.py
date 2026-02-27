from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend import models
from Backend.create_tables import _CreateTablesWorkflow
from Backend.crud_fornecedor_import_jobs import _FornecedorImportJobWorkflow
from Backend.crud_fornecedores import _FornecedorCrudWorkflow
from Backend.crud_historico import _HistoricoCrudWorkflow
from Backend.crud_product_types import _ProductTypeCrudWorkflow
from Backend.crud_produtos import _ProdutoCrudWorkflow
from Backend.crud_registros_uso_ia import _RegistroUsoIACrudWorkflow
from Backend.crud_users import _UserCrudWorkflow
from Backend.database import _DatabaseWorkflow
from Backend.initial_data import _InitialDataWorkflow
from Backend.testing.runtime_apis import (
    _CatalogStorageWorkflow,
    _LineMappingWorkflow,
    _PdfJobWorkflow,
    _TabularIngestionWorkflow,
    _TabularPreviewWorkflow,
    _WebExtractionEnrichmentWorkflow,
)
from Backend.tasks import _TaskWorkflow


def test_create_tables_workflow_delega_runtime_injetado():
    called = []

    class FakeRuntime:
        def create_all_tables(self):
            called.append("ok")

    workflow = _CreateTablesWorkflow(runtime=FakeRuntime())
    workflow.create_all_tables()

    assert called == ["ok"]


def test_database_workflow_delega_runtime_injetado():
    called = []

    class FakeRuntime:
        def build_engine_args(self, database_url: str):
            called.append(("build", database_url))
            return {"db": database_url}

        def get_db(self):
            called.append(("get_db",))
            yield "db-session"

    workflow = _DatabaseWorkflow(runtime=FakeRuntime())
    args = workflow.build_engine_args("sqlite://")
    sessions = list(workflow.get_db())

    assert args == {"db": "sqlite://"}
    assert sessions == ["db-session"]
    assert called == [("build", "sqlite://"), ("get_db",)]


def test_task_workflow_delega_runtime_injetado():
    called = []

    class FakeRuntime:
        def process_pdf_extraction_task(self, *, import_job_id, page_number, db_url):
            called.append((import_job_id, page_number, db_url))

    workflow = _TaskWorkflow(runtime=FakeRuntime())
    workflow.process_pdf_extraction_task(import_job_id=10, page_number=2, db_url="db-url")

    assert called == [(10, 2, "db-url")]


def test_line_mapping_workflow_delega_runtime_injetado():
    class FakeRuntime:
        def processar_linha_padronizada(self, *, linha_original, mapeamento_colunas_usuario=None):
            return {
                "nome_base": linha_original.get("nome"),
                "mapping": mapeamento_colunas_usuario,
            }

    workflow = _LineMappingWorkflow(runtime=FakeRuntime())
    result = workflow.processar_linha_padronizada(
        {"nome": "Produto X"},
        {"nome": "nome_base"},
    )

    assert result == {"nome_base": "Produto X", "mapping": {"nome": "nome_base"}}


def test_crud_workflows_delegam_runtime_injetado_bloco_1():
    class FornecedorRuntime:
        def create_fornecedor(self, **kwargs):
            return {"workflow": "fornecedor", **kwargs}

    class ProductTypeRuntime:
        def reorder_attribute_template(self, **kwargs):
            return {"workflow": "product_type", **kwargs}

    class HistoricoRuntime:
        def count_registros_historico(self, **kwargs):
            return 42

    fornecedor_workflow = _FornecedorCrudWorkflow(runtime=FornecedorRuntime())
    product_type_workflow = _ProductTypeCrudWorkflow(runtime=ProductTypeRuntime())
    historico_workflow = _HistoricoCrudWorkflow(runtime=HistoricoRuntime())

    created = fornecedor_workflow.create_fornecedor(db="db", fornecedor="schema", user_id=7)
    reordered = product_type_workflow.reorder_attribute_template(
        db="db",
        attribute_id=10,
        direction="up",
    )
    count = historico_workflow.count_registros_historico(db="db")

    assert created["workflow"] == "fornecedor"
    assert reordered["workflow"] == "product_type"
    assert count == 42


@pytest.mark.asyncio
async def test_crud_workflows_delegam_runtime_injetado_bloco_2():
    class ProdutoRuntime:
        def create_produto(self, **kwargs):
            return {"workflow": "produto", **kwargs}

        async def save_produto_image(self, **kwargs):
            return f"/tmp/{kwargs['produto_id']}.png"

    class UserRuntime:
        def get_user(self, **kwargs):
            return {"workflow": "user", **kwargs}

    class RegistroUsoRuntime:
        def get_geracoes_ia_count_no_mes_corrente(self, **kwargs):
            return 9

    class JobRuntime:
        def update_job_status(self, **kwargs):
            return {"workflow": "job", **kwargs}

    class InitialDataRuntime:
        def create_initial_data(self, **kwargs):
            return {"workflow": "initial_data", **kwargs}

    produto_workflow = _ProdutoCrudWorkflow(runtime=ProdutoRuntime())
    user_workflow = _UserCrudWorkflow(runtime=UserRuntime())
    registro_workflow = _RegistroUsoIACrudWorkflow(runtime=RegistroUsoRuntime())
    job_workflow = _FornecedorImportJobWorkflow(runtime=JobRuntime())
    initial_data_workflow = _InitialDataWorkflow(runtime=InitialDataRuntime())

    produto = produto_workflow.create_produto(db="db", produto="schema", user_id=1)
    image_path = await produto_workflow.save_produto_image(db="db", produto_id=88, file="img")
    user = user_workflow.get_user(db="db", user_id=3)
    total = registro_workflow.get_geracoes_ia_count_no_mes_corrente(db="db", user_id=3)
    job = job_workflow.update_job_status(db="db", job="job", status="DONE")
    initial = initial_data_workflow.create_initial_data(db="db")

    assert produto["workflow"] == "produto"
    assert image_path == "/tmp/88.png"
    assert user["workflow"] == "user"
    assert total == 9
    assert job["workflow"] == "job"
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

    workflow = _CatalogStorageWorkflow(runtime=FakeRuntime())
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

    ingestion = _TabularIngestionWorkflow(runtime=FakeIngestionRuntime())
    preview = _TabularPreviewWorkflow(runtime=FakePreviewRuntime())

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

    workflow = _PdfJobWorkflow(runtime=FakeRuntime())
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
    workflow = _WebExtractionEnrichmentWorkflow(
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

