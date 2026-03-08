"""Coverage for file processing runtime/workflow composition wrappers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.testing.runtime_apis import file_processing


@pytest.mark.asyncio
async def test_catalog_storage_and_tabular_wrappers_delegate(monkeypatch):
    calls = []

    async def fake_save_uploaded_catalog_impl(*, file, fornecedor_id=None):
        calls.append(("save_uploaded_catalog_impl", file, fornecedor_id))
        return {"file": file, "fornecedor_id": fornecedor_id}

    def fake_delete_catalog_file_impl(stored_filename):
        calls.append(("delete_catalog_file_impl", stored_filename))

    def fake_get_file_path_by_id_impl(*, db, file_id):
        calls.append(("get_file_path_by_id_impl", db, file_id))
        return f"/tmp/{file_id}"

    async def fake_processar_arquivo_excel_impl(**kwargs):
        calls.append(("processar_arquivo_excel_impl", kwargs))
        return [kwargs]

    async def fake_processar_arquivo_csv_impl(**kwargs):
        calls.append(("processar_arquivo_csv_impl", kwargs))
        return [kwargs]

    async def fake_preview_arquivo_excel_impl(**kwargs):
        calls.append(("preview_arquivo_excel_impl", kwargs))
        return {"headers": ["a"], "sample_rows": []}

    async def fake_preview_arquivo_csv_impl(**kwargs):
        calls.append(("preview_arquivo_csv_impl", kwargs))
        return {"headers": ["b"], "sample_rows": []}

    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_save_uploaded_catalog_impl", fake_save_uploaded_catalog_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_delete_catalog_file_impl", fake_delete_catalog_file_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_get_file_path_by_id_impl", fake_get_file_path_by_id_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_processar_arquivo_excel_impl", fake_processar_arquivo_excel_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_processar_arquivo_csv_impl", fake_processar_arquivo_csv_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_preview_arquivo_excel_impl", fake_preview_arquivo_excel_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_preview_arquivo_csv_impl", fake_preview_arquivo_csv_impl)

    catalog_runtime = file_processing.CatalogStorageRuntime()
    assert await catalog_runtime.save_uploaded_catalog(file="catalogo.pdf", fornecedor_id=9) == {"file": "catalogo.pdf", "fornecedor_id": 9}
    catalog_runtime.delete_catalog_file("catalogo.pdf")
    assert catalog_runtime.get_file_path_by_id(db="db", file_id="77") == "/tmp/77"

    catalog_workflow = file_processing.CatalogStorageWorkflow(runtime=catalog_runtime)
    assert await catalog_workflow.save_uploaded_catalog(file="catalogo-2.pdf", fornecedor_id=None) == {"file": "catalogo-2.pdf", "fornecedor_id": None}
    catalog_workflow.delete_catalog_file("catalogo-2.pdf")
    assert catalog_workflow.get_file_path_by_id(db="db2", file_id="88") == "/tmp/88"

    ingestion_runtime = file_processing.TabularIngestionRuntime()
    assert await ingestion_runtime.processar_arquivo_excel(conteudo_arquivo=b"x", mapeamento_colunas_usuario={"a": "b"}, sheet_name="Plan1", product_type_id=3) == [{"conteudo_arquivo": b"x", "mapeamento_colunas_usuario": {"a": "b"}, "sheet_name": "Plan1", "product_type_id": 3}]
    assert await ingestion_runtime.processar_arquivo_csv(conteudo_arquivo=b"y", mapeamento_colunas_usuario={"x": "y"}, product_type_id=4) == [{"conteudo_arquivo": b"y", "mapeamento_colunas_usuario": {"x": "y"}, "product_type_id": 4}]

    ingestion_workflow = file_processing.TabularIngestionWorkflow(runtime=ingestion_runtime)
    assert await ingestion_workflow.processar_arquivo_excel(conteudo_arquivo=b"z") == [{"conteudo_arquivo": b"z", "mapeamento_colunas_usuario": None, "sheet_name": None, "product_type_id": None}]
    assert await ingestion_workflow.processar_arquivo_csv(conteudo_arquivo=b"w") == [{"conteudo_arquivo": b"w", "mapeamento_colunas_usuario": None, "product_type_id": None}]

    preview_runtime = file_processing.TabularPreviewRuntime()
    assert await preview_runtime.preview_arquivo_excel(conteudo_arquivo=b"x") == {"headers": ["a"], "sample_rows": []}
    assert await preview_runtime.preview_arquivo_csv(conteudo_arquivo=b"y") == {"headers": ["b"], "sample_rows": []}

    preview_workflow = file_processing.TabularPreviewWorkflow(runtime=preview_runtime)
    assert await preview_workflow.preview_arquivo_excel(conteudo_arquivo=b"x", max_rows=2) == {"headers": ["a"], "sample_rows": []}
    assert await preview_workflow.preview_arquivo_csv(conteudo_arquivo=b"y", max_rows=3) == {"headers": ["b"], "sample_rows": []}


@pytest.mark.asyncio
async def test_pdf_asset_and_processing_wrappers_delegate(monkeypatch):
    calls = []

    async def fake_pdf_pages_to_images(*, conteudo_arquivo, max_pages=1, start_page=1, dpi=200):
        calls.append(("pdf_bytes_to_images", conteudo_arquivo, max_pages, start_page, dpi))
        return ["img-1"]

    def fake_generate_pdf_page_images(*, file_path, file_id):
        calls.append(("generate_pdf_page_images", file_path, file_id))
        return [f"{file_id}.png"]

    def fake_extract_pdf_region_image(*, file_path, page_number, region=None, dpi=300):
        calls.append(("extract_pdf_region_image", file_path, page_number, region, dpi))
        return b"region"

    def fake_parse_annotation_to_dataframe(*, annotation, vertical_tolerance=5):
        calls.append(("parse_annotation_to_dataframe", annotation, vertical_tolerance))
        return {"annotation": annotation, "vertical_tolerance": vertical_tolerance}

    def fake_pdf_pages_to_images_impl(**kwargs):
        calls.append(("pdf_pages_to_images_impl", kwargs))
        return {"pages": 2}

    async def fake_extrair_pagina_pdf_impl(**kwargs):
        calls.append(("extrair_pagina_pdf_impl", kwargs))
        return {"page_number": kwargs["page_number"]}

    def fake_extract_data_from_pdf_region_impl(**kwargs):
        calls.append(("extract_data_from_pdf_region_impl", kwargs))
        return {"region": kwargs["region"]}

    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_pdf_pages_to_images_impl", fake_pdf_pages_to_images_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_extrair_pagina_pdf_impl", fake_extrair_pagina_pdf_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_extract_data_from_pdf_region_impl", fake_extract_data_from_pdf_region_impl)

    asset_runtime = file_processing.PdfAssetRuntime(
        pdf_image_runtime=SimpleNamespace(pdf_bytes_to_images=fake_pdf_pages_to_images),
        pdf_asset_runtime=SimpleNamespace(
            generate_pdf_page_images=fake_generate_pdf_page_images,
            extract_pdf_region_image=fake_extract_pdf_region_image,
            parse_annotation_to_dataframe=fake_parse_annotation_to_dataframe,
        ),
    )
    async def fake_override_pdf_bytes_to_images(**kwargs):
        calls.append(("override_pdf_bytes_to_images", kwargs))
        return ["override"]

    override_asset_runtime = SimpleNamespace(
        pdf_image_runtime=SimpleNamespace(pdf_bytes_to_images=fake_override_pdf_bytes_to_images),
        pdf_asset_runtime=asset_runtime.pdf_asset_runtime,
    )
    assert asset_runtime.apply_overrides(override_asset_runtime) is asset_runtime
    assert await asset_runtime.pdf_image_runtime.pdf_bytes_to_images(conteudo_arquivo=b"pdf") == ["override"]

    asset_workflow = file_processing.PdfAssetWorkflow(runtime=SimpleNamespace(pdf_image_runtime=SimpleNamespace(pdf_bytes_to_images=fake_pdf_pages_to_images), pdf_asset_runtime=asset_runtime.pdf_asset_runtime))
    assert await asset_workflow.pdf_bytes_to_images(conteudo_arquivo=b"pdf", max_pages=2, start_page=3, dpi=150) == ["img-1"]
    assert asset_workflow.pdf_pages_to_images(db="db", file="arquivo.pdf", fornecedor_id=1, user_id=2, offset=0, limit=10) == {"pages": 2}
    assert await asset_workflow.extrair_pagina_pdf(conteudo_pdf=b"pdf", page_number=4, region=[1, 2, 3, 4]) == {"page_number": 4}
    assert asset_workflow.generate_pdf_page_images(file_path="/tmp/a.pdf", file_id="77") == ["77.png"]
    assert asset_workflow.extract_pdf_region_image(file_path="/tmp/a.pdf", page_number=2, region=[1, 2, 3, 4], dpi=144) == b"region"
    assert asset_workflow.parse_annotation_to_dataframe(annotation="ann", vertical_tolerance=7) == {"annotation": "ann", "vertical_tolerance": 7}

    async def fake_processing_pdf_ingestion(**kwargs):
        _ = kwargs
        return None

    async def fake_processing_pdf_preview(**kwargs):
        _ = kwargs
        return None

    async def fake_processing_preview_dispatch(**kwargs):
        _ = kwargs
        return None

    processing_runtime = file_processing.PdfProcessingRuntime(
        pdf_ingestion_runtime=SimpleNamespace(processar_arquivo_pdf=fake_processing_pdf_ingestion),
        pdf_preview_runtime=SimpleNamespace(preview_arquivo_pdf=fake_processing_pdf_preview),
        preview_dispatch_runtime=SimpleNamespace(gerar_preview=fake_processing_preview_dispatch),
        ocr_runtime_state=SimpleNamespace(),
    )
    override_processing_runtime = SimpleNamespace(
        pdf_ingestion_runtime=SimpleNamespace(processar_arquivo_pdf=fake_processing_pdf_ingestion),
        pdf_preview_runtime=SimpleNamespace(preview_arquivo_pdf=fake_processing_pdf_preview),
        preview_dispatch_runtime=SimpleNamespace(gerar_preview=fake_processing_preview_dispatch),
        extract_data_from_pdf_region=lambda **kwargs: {"override_region": True},
        ocr_runtime_state=SimpleNamespace(name="ocr"),
    )
    assert processing_runtime.apply_overrides(override_processing_runtime) is processing_runtime
    assert processing_runtime.extract_data_from_pdf_region(file_path="/tmp/a.pdf", page_number=1) == {"override_region": True}

    class FakePdfProcessingWorkflowRuntime:
        def __init__(self):
            async def workflow_processar_pdf(**kwargs):
                return [{"ingested": kwargs["product_type_id"]}]

            async def workflow_preview_pdf(**kwargs):
                return {"preview": kwargs["ext"]}

            async def workflow_gerar_preview(**kwargs):
                return {"dispatch": kwargs["ext"]}

            self.pdf_ingestion_runtime = SimpleNamespace(processar_arquivo_pdf=workflow_processar_pdf)
            self.pdf_preview_runtime = SimpleNamespace(preview_arquivo_pdf=workflow_preview_pdf)
            self.preview_dispatch_runtime = SimpleNamespace(gerar_preview=workflow_gerar_preview)
            self.extract_data_from_pdf_region = lambda **kwargs: {"region": kwargs["region"]}

    pdf_processing_workflow = file_processing.PdfProcessingWorkflow(runtime=FakePdfProcessingWorkflowRuntime())
    assert await pdf_processing_workflow.processar_arquivo_pdf(conteudo_arquivo=b"pdf", product_type_id=5) == [{"ingested": 5}]
    assert await pdf_processing_workflow.preview_arquivo_pdf(conteudo_arquivo=b"pdf", ext=".pdf") == {"preview": ".pdf"}
    assert await pdf_processing_workflow.gerar_preview(conteudo_arquivo=b"pdf", ext=".csv", max_rows=9) == {"dispatch": ".csv"}
    assert pdf_processing_workflow.extract_data_from_pdf_region(file_path="/tmp/a.pdf", page_number=1, region=[1, 2, 3, 4]) == {"region": [1, 2, 3, 4]}


@pytest.mark.asyncio
async def test_pdf_job_and_file_processing_runtime_delegate(monkeypatch):
    calls = []

    async def fake_process_pdf_job_impl(**kwargs):
        calls.append(("process_pdf_job_impl", kwargs))

    def fake_extract_data_from_single_page_impl(**kwargs):
        calls.append(("extract_data_from_single_page_impl", kwargs))
        return {"page_number": kwargs["page_number"]}

    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_process_pdf_job_impl", fake_process_pdf_job_impl)
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_extract_data_from_single_page_impl", fake_extract_data_from_single_page_impl)

    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    session_provider = SimpleNamespace(open_session=lambda: session)
    pdf_job_runtime = file_processing.PdfJobRuntime(
        session_provider=session_provider,
        catalog_import_file_repository_factory=lambda session_obj: {"session": session_obj},
    )
    await pdf_job_runtime.process_pdf_job(job_id=11, pdf_path="/tmp/a.pdf", start_page=2, mapping={"x": "y"})
    assert session.closed is True
    assert pdf_job_runtime.extract_data_from_single_page(file_path="/tmp/a.pdf", page_number=3) == {"page_number": 3}

    pdf_job_workflow = file_processing.PdfJobWorkflow(runtime=SimpleNamespace(
        process_pdf_job=fake_process_pdf_job_impl,
        extract_data_from_single_page=fake_extract_data_from_single_page_impl,
    ))
    await pdf_job_workflow.process_pdf_job(job_id=12, pdf_path="/tmp/b.pdf", start_page=1, mapping=None)
    assert pdf_job_workflow.extract_data_from_single_page(file_path="/tmp/b.pdf", page_number=4) == {"page_number": 4}

    class FakeCatalogStorage:
        async def save_uploaded_catalog(self, **kwargs):
            return {"save": kwargs["fornecedor_id"]}

        def delete_catalog_file(self, **kwargs):
            return {"delete": kwargs["stored_filename"]}

        def get_file_path_by_id(self, **kwargs):
            return f"path:{kwargs['file_id']}"

    class FakeTabularIngestion:
        async def processar_arquivo_excel(self, **kwargs):
            return [{"excel": kwargs["product_type_id"]}]

        async def processar_arquivo_csv(self, **kwargs):
            return [{"csv": kwargs["product_type_id"]}]

    class FakeTabularPreview:
        async def preview_arquivo_excel(self, **kwargs):
            return {"preview_excel": kwargs["max_rows"]}

        async def preview_arquivo_csv(self, **kwargs):
            return {"preview_csv": kwargs["max_rows"]}

    class FakePdfAsset:
        async def pdf_bytes_to_images(self, **kwargs):
            return [kwargs["dpi"]]

        def pdf_pages_to_images(self, **kwargs):
            return {"offset": kwargs["offset"]}

        async def extrair_pagina_pdf(self, **kwargs):
            return {"page": kwargs["page_number"]}

        def generate_pdf_page_images(self, **kwargs):
            return [kwargs["file_id"]]

        def extract_pdf_region_image(self, **kwargs):
            return kwargs["dpi"]

        def parse_annotation_to_dataframe(self, **kwargs):
            return {"vertical_tolerance": kwargs["vertical_tolerance"]}

    class FakePdfProcessing:
        async def processar_arquivo_pdf(self, **kwargs):
            return [{"pdf": kwargs["extraction_mode"]}]

        async def preview_arquivo_pdf(self, **kwargs):
            return {"preview_pdf": kwargs["ext"]}

        async def gerar_preview(self, **kwargs):
            return {"gerar_preview": kwargs["ext"]}

        def extract_data_from_pdf_region(self, **kwargs):
            return {"region": kwargs["region"]}

    class FakePdfJob:
        async def process_pdf_job(self, **kwargs):
            return {"job": kwargs["job_id"]}

        def extract_data_from_single_page(self, **kwargs):
            return {"single_page": kwargs["page_number"]}

    class FakeLineMapping:
        def processar_linha_padronizada(self, **kwargs):
            return {"linha": kwargs["linha_original"]}

    runtime = file_processing.FileProcessingRuntime(
        catalog_storage_workflow=FakeCatalogStorage(),
        line_mapping_workflow=FakeLineMapping(),
        tabular_ingestion_workflow=FakeTabularIngestion(),
        tabular_preview_workflow=FakeTabularPreview(),
        pdf_asset_workflow=FakePdfAsset(),
        pdf_processing_workflow=FakePdfProcessing(),
        pdf_job_workflow=FakePdfJob(),
    )

    assert await runtime.save_uploaded_catalog(file="catalogo.pdf", fornecedor_id=8) == {"save": 8}
    assert runtime.delete_catalog_file("catalogo.pdf") == {"delete": "catalogo.pdf"}
    assert runtime.get_file_path_by_id(db="db", file_id="99") == "path:99"
    assert await runtime.processar_arquivo_excel(conteudo_arquivo=b"x", product_type_id=3) == [{"excel": 3}]
    assert await runtime.processar_arquivo_csv(conteudo_arquivo=b"y", product_type_id=4) == [{"csv": 4}]
    assert await runtime.processar_arquivo_pdf(conteudo_arquivo=b"pdf", extraction_mode="ocr") == [{"pdf": "ocr"}]
    assert await runtime.preview_arquivo_excel(conteudo_arquivo=b"x", max_rows=2) == {"preview_excel": 2}
    assert await runtime.preview_arquivo_csv(conteudo_arquivo=b"y", max_rows=3) == {"preview_csv": 3}
    assert await runtime.preview_arquivo_pdf(conteudo_arquivo=b"pdf", ext=".pdf", dpi=144) == {"preview_pdf": ".pdf"}
    assert await runtime.gerar_preview(conteudo_arquivo=b"csv", ext=".csv", max_rows=6) == {"gerar_preview": ".csv"}
    assert await runtime.pdf_bytes_to_images(conteudo_arquivo=b"pdf", dpi=200) == [200]
    assert runtime.pdf_pages_to_images(db="db", file="file", fornecedor_id=1, user_id=2, offset=3, limit=4) == {"offset": 3}
    assert await runtime.extrair_pagina_pdf(conteudo_pdf=b"pdf", page_number=5, region=[1, 2, 3, 4]) == {"page": 5}
    assert runtime.generate_pdf_page_images(file_path="/tmp/a.pdf", file_id="123") == ["123"]
    assert runtime.extract_pdf_region_image(file_path="/tmp/a.pdf", page_number=1, region=None, dpi=144) == 144
    assert runtime.parse_annotation_to_dataframe(annotation="ann", vertical_tolerance=8) == {"vertical_tolerance": 8}
    assert runtime.extract_data_from_pdf_region(file_path="/tmp/a.pdf", page_number=1, region=[0, 1, 2, 3]) == {"region": [0, 1, 2, 3]}
    assert await runtime.process_pdf_job(job_id=55, pdf_path="/tmp/a.pdf") == {"job": 55}
    assert runtime.extract_data_from_single_page(file_path="/tmp/a.pdf", page_number=6) == {"single_page": 6}
    assert runtime.processar_linha_padronizada(linha_original={"a": 1}, mapeamento_colunas_usuario={"a": "b"}) == {"linha": {"a": 1}}
