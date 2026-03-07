import fornecedorService from '../fornecedorService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

describe('fornecedorService', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('getFornecedores forwards params and returns the API payload', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: { items: [{ id: 1 }], total_items: 1, limit: 10, skip: 0 },
    });

    const result = await fornecedorService.getFornecedores({ skip: 5, termo_busca: 'abc' });

    expect(apiClient.get).toHaveBeenCalledWith('/fornecedores/', {
      params: { skip: 5, termo_busca: 'abc' },
    });
    expect(result).toEqual({ items: [{ id: 1 }], total_items: 1, limit: 10, skip: 0 });
  });

  test('getFornecedores rethrows backend payload and request errors explicitly', async () => {
    apiClient.get
      .mockRejectedValueOnce({ response: { data: { detail: 'backend' } } })
      .mockRejectedValueOnce({ request: {} });

    await expect(fornecedorService.getFornecedores()).rejects.toEqual({ detail: 'backend' });
    await expect(fornecedorService.getFornecedores()).rejects.toThrow(
      'Nenhuma resposta do servidor ao buscar fornecedores.'
    );
  });

  test('getFornecedorById, createFornecedor, updateFornecedor and deleteFornecedor use the expected endpoints', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { id: 2 } });
    apiClient.post.mockResolvedValueOnce({ data: { id: 3 } });
    apiClient.put.mockResolvedValueOnce({ data: { id: 2, nome: 'Atualizado' } });
    apiClient.delete.mockResolvedValueOnce({ data: { deleted: true } });

    await expect(fornecedorService.getFornecedorById(2)).resolves.toEqual({ id: 2 });
    await expect(fornecedorService.createFornecedor({ nome: 'Novo' })).resolves.toEqual({
      id: 3,
    });
    await expect(fornecedorService.updateFornecedor(2, { nome: 'Atualizado' })).resolves.toEqual({
      id: 2,
      nome: 'Atualizado',
    });
    await expect(fornecedorService.deleteFornecedor(2)).resolves.toEqual({ deleted: true });

    expect(apiClient.get).toHaveBeenCalledWith('/fornecedores/2');
    expect(apiClient.post).toHaveBeenCalledWith('/fornecedores/', { nome: 'Novo' });
    expect(apiClient.put).toHaveBeenCalledWith('/fornecedores/2', { nome: 'Atualizado' });
    expect(apiClient.delete).toHaveBeenCalledWith('/fornecedores/2');
  });

  test('setFornecedorMapping saves mapping and falls back to a generic error message', async () => {
    apiClient.put
      .mockResolvedValueOnce({ data: { ok: true } })
      .mockRejectedValueOnce(new Error('timeout'));

    await expect(
      fornecedorService.setFornecedorMapping(7, { sku: 'codigo' })
    ).resolves.toEqual({ ok: true });
    await expect(fornecedorService.setFornecedorMapping(7, {})).rejects.toThrow(
      'timeout'
    );

    expect(apiClient.put).toHaveBeenNthCalledWith(1, '/fornecedores/7/mapping', {
      sku: 'codigo',
    });
  });

  test('previewCatalogo sends a multipart payload and maps preview fields to camelCase', async () => {
    const file = new File(['conteudo'], 'catalogo.pdf', { type: 'application/pdf' });
    apiClient.post.mockResolvedValueOnce({
      data: {
        file_id: 90,
        headers: ['SKU'],
        sample_rows: [['001']],
        preview_images: ['img1'],
        num_pages: 6,
        table_pages: [1, 2],
      },
    });

    const result = await fornecedorService.previewCatalogo(file, 12, 3, 77);
    const [endpoint, formData] = apiClient.post.mock.calls[0];

    expect(endpoint).toBe('/produtos/importar-catalogo-preview/');
    expect(formData.get('file')).toBe(file);
    expect(formData.get('page_count')).toBe('12');
    expect(formData.get('start_page')).toBe('3');
    expect(formData.get('fornecedor_id')).toBe('77');
    expect(result).toEqual({
      fileId: 90,
      headers: ['SKU'],
      sampleRows: [['001']],
      previewImages: ['img1'],
      numPages: 6,
      tablePages: [1, 2],
    });
  });

  test('importCatalogo includes mapping when provided and handles request failures', async () => {
    const file = new File(['conteudo'], 'catalogo.xlsx');
    apiClient.post
      .mockResolvedValueOnce({ data: { ok: true } })
      .mockRejectedValueOnce({ request: {} });

    await expect(
      fornecedorService.importCatalogo(5, file, { sku: 'codigo' })
    ).resolves.toEqual({ ok: true });

    const [endpoint, formData] = apiClient.post.mock.calls[0];
    expect(endpoint).toBe('/produtos/importar-catalogo/5/');
    expect(formData.get('file')).toBe(file);
    expect(formData.get('mapeamento_colunas_usuario')).toBe('{"sku":"codigo"}');

    await expect(fornecedorService.importCatalogo(5, file)).rejects.toThrow(
      'Nenhuma resposta do servidor ao tentar importar catálogo.'
    );
  });

  test('catalog import maintenance endpoints use the expected HTTP calls', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [] } });
    apiClient.delete.mockResolvedValueOnce({ data: { deleted: true } });
    apiClient.post.mockResolvedValueOnce({ data: { status: 'queued' } });
    apiClient.get.mockResolvedValueOnce({ data: { status: 'PROCESSING' } });

    await expect(fornecedorService.getCatalogImportFiles({ status: 'DONE' })).resolves.toEqual({
      items: [],
    });
    await expect(fornecedorService.deleteCatalogFile(8)).resolves.toEqual({ deleted: true });
    await expect(
      fornecedorService.reprocessCatalogFile(8, { force: true })
    ).resolves.toEqual({ status: 'queued' });
    await expect(fornecedorService.getImportacaoStatus(8)).resolves.toEqual({
      status: 'PROCESSING',
    });

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/produtos/catalog-import-files/', {
      params: { status: 'DONE' },
    });
    expect(apiClient.delete).toHaveBeenCalledWith('/produtos/catalog-import-files/8/');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/produtos/catalog-import-files/8/reprocess/',
      { force: true }
    );
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/produtos/importar-catalogo-status/8');
  });

  test('getImportacaoResult distinguishes between processing and ready states', async () => {
    apiClient.get
      .mockResolvedValueOnce({
        status: 202,
        data: { status: 'PROCESSING', detail: 'ainda rodando' },
      })
      .mockResolvedValueOnce({
        status: 200,
        data: { status: 'DONE', produtos_criados: 10 },
      });

    await expect(fornecedorService.getImportacaoResult(11)).resolves.toEqual({
      ready: false,
      status: 'PROCESSING',
      detail: 'ainda rodando',
    });
    await expect(fornecedorService.getImportacaoResult(12)).resolves.toEqual({
      ready: true,
      status: 'DONE',
      produtos_criados: 10,
    });
  });

  test('getImportacaoResult rethrows backend payload enriched with http status', async () => {
    apiClient.get.mockRejectedValueOnce({
      response: {
        status: 404,
        data: { detail: 'nao encontrado' },
      },
    });

    await expect(fornecedorService.getImportacaoResult(99)).rejects.toEqual({
      detail: 'nao encontrado',
      http_status: 404,
    });
  });

  test('uploadForPagePreview and getPdfPreview map preview payloads', async () => {
    const file = new File(['conteudo'], 'catalogo.pdf', { type: 'application/pdf' });
    apiClient.post
      .mockResolvedValueOnce({
        data: { import_file_id: 55, image_urls: ['a.png'] },
      })
      .mockResolvedValueOnce({
        data: { image_urls: ['b.png'], total_pages: 30 },
      });

    await expect(fornecedorService.uploadForPagePreview(file, 3)).resolves.toEqual({
      fileId: 55,
      image_urls: ['a.png'],
    });
    await expect(fornecedorService.getPdfPreview(file, 3, 10, 2)).resolves.toEqual({
      image_urls: ['b.png'],
      total_pages: 30,
    });

    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/fornecedores/3/preview-pdf',
      expect.any(FormData)
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/fornecedores/3/preview-pdf',
      expect.any(FormData),
      { params: { offset: 10, limit: 2 } }
    );
  });

  test('mapping, progress and commit endpoints pass params and payloads correctly', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { linhas: [] } })
      .mockResolvedValueOnce({ data: { progresso: 50 } })
      .mockResolvedValueOnce({ data: { review: [] } });
    apiClient.post
      .mockResolvedValueOnce({ data: { job_id: 'abc' } })
      .mockResolvedValueOnce({ data: { done: true } });

    await expect(fornecedorService.fetchPageDataForMapping(90, 4)).resolves.toEqual({
      linhas: [],
    });
    await expect(
      fornecedorService.startFullProcess({ file_id: 90, fornecedor_id: 2 })
    ).resolves.toEqual({ job_id: 'abc' });
    await expect(fornecedorService.getImportProgress('job-1')).resolves.toEqual({
      progresso: 50,
    });
    await expect(fornecedorService.getReviewData('job-1', { page: 1 })).resolves.toEqual({
      review: [],
    });
    await expect(fornecedorService.commitImport('job-1')).resolves.toEqual({ done: true });

    expect(apiClient.get).toHaveBeenNthCalledWith(
      1,
      '/fornecedores/import/extract-page-data',
      { params: { file_id: 90, page_number: 4 } }
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/fornecedores/import/process-full-catalog',
      { file_id: 90, fornecedor_id: 2 }
    );
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/fornecedores/import/progress/job-1');
    expect(apiClient.get).toHaveBeenNthCalledWith(
      3,
      '/fornecedores/import/review/job-1',
      { params: { page: 1 } }
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(2, '/fornecedores/import/commit/job-1');
  });

  test('region selection and finalization endpoints build the expected payloads', async () => {
    apiClient.post
      .mockResolvedValueOnce({ data: { ok: 'preview' } })
      .mockResolvedValueOnce({ data: { ok: 'bulk' } })
      .mockResolvedValueOnce({ data: { ok: 'produto' } })
      .mockResolvedValueOnce({ data: { ok: 'finalizar' } });

    await expect(
      fornecedorService.selecionarRegiao({
        fileId: 1,
        pageNumber: 2,
        bbox: { x: 1, y: 2 },
      })
    ).resolves.toEqual({ ok: 'preview' });
    await expect(
      fornecedorService.extractRegionBulk({
        fileId: 1,
        bbox: { x: 3, y: 4 },
        pages: [2, 3],
        allPages: true,
      })
    ).resolves.toEqual({ ok: 'bulk' });
    await expect(
      fornecedorService.selecionarRegiaoProduto({
        fileId: 1,
        pageNumber: 4,
        bbox: { x: 5, y: 6 },
        bboxNorm: { x: 0.1, y: 0.2 },
        canvasWidth: 800,
        canvasHeight: 600,
      })
    ).resolves.toEqual({ ok: 'produto' });
    await expect(
      fornecedorService.finalizarImportacaoCatalogo({
        fileId: 44,
        productTypeId: 7,
        fornecedorId: 8,
        mapping: { sku: 'codigo' },
        pages: [1, 2],
        region: { x: 1 },
      })
    ).resolves.toEqual({ ok: 'finalizar' });

    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/fornecedores/preview-catalog-region',
      {
        file_id: 1,
        page_number: 2,
        region: { x: 1, y: 2 },
      }
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/fornecedores/extract_data_from_pdf_bulk',
      {
        file_id: 1,
        region: { x: 3, y: 4 },
        pages: [2, 3],
        all_pages: true,
      }
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      3,
      '/produtos/selecionar-regiao/',
      {
        file_id: 1,
        page: 4,
        bbox: { x: 5, y: 6 },
        bbox_norm: { x: 0.1, y: 0.2 },
        canvas_width: 800,
        canvas_height: 600,
      }
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      4,
      '/produtos/importar-catalogo-finalizar/44/',
      {
        product_type_id: 7,
        fornecedor_id: 8,
        mapping: { sku: 'codigo' },
        pages: [1, 2],
        region: { x: 1 },
        extraction_mode: 'ocr',
      }
    );
  });
});
