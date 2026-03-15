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
    jest.resetAllMocks();
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

  test('getFornecedores falls back to a generic configuration error when the failure is empty', async () => {
    apiClient.get.mockRejectedValueOnce({});

    await expect(fornecedorService.getFornecedores()).rejects.toThrow(
      /Erro ao configurar requisi.*buscar fornecedores/i
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

  test('resolveFornecedorLogo uses the dedicated endpoint and returns the payload', async () => {
    apiClient.post.mockResolvedValueOnce({
      data: {
        logo_url: 'https://cdn.example.com/logo.png',
        resolved_site_url: 'https://empresa.example',
        source: 'img-logo',
      },
    });

    await expect(
      fornecedorService.resolveFornecedorLogo('empresa.example')
    ).resolves.toEqual({
      logo_url: 'https://cdn.example.com/logo.png',
      resolved_site_url: 'https://empresa.example',
      source: 'img-logo',
    });

    expect(apiClient.post).toHaveBeenCalledWith('/fornecedores/resolve-logo', {
      site_url: 'empresa.example',
    });
  });

  test('core fornecedor endpoints surface request and generic failures', async () => {
    apiClient.get
      .mockRejectedValueOnce({ request: {} })
      .mockRejectedValueOnce(new Error('config get'));
    apiClient.post.mockRejectedValueOnce(new Error('create timeout'));
    apiClient.put
      .mockRejectedValueOnce({ request: {} })
      .mockRejectedValueOnce(new Error('config put'));
    apiClient.delete
      .mockRejectedValueOnce({ request: {} })
      .mockRejectedValueOnce(new Error('config delete'));

    await expect(fornecedorService.getFornecedorById(4)).rejects.toThrow(
      /Nenhuma resposta do servidor ao buscar fornecedor 4/i
    );
    await expect(fornecedorService.getFornecedorById(4)).rejects.toThrow('config get');
    await expect(fornecedorService.createFornecedor({ nome: 'Novo' })).rejects.toThrow(
      'create timeout'
    );
    await expect(fornecedorService.updateFornecedor(4, { nome: 'Novo' })).rejects.toThrow(
      /Nenhuma resposta do servidor ao tentar atualizar fornecedor 4/i
    );
    await expect(fornecedorService.updateFornecedor(4, { nome: 'Novo' })).rejects.toThrow(
      'config put'
    );
    await expect(fornecedorService.deleteFornecedor(4)).rejects.toThrow(
      /Nenhuma resposta do servidor ao tentar deletar fornecedor 4/i
    );
    await expect(fornecedorService.deleteFornecedor(4)).rejects.toThrow('config delete');
  });

  test('core fornecedor endpoints rethrow backend payloads when available', async () => {
    apiClient.get.mockRejectedValueOnce({ response: { data: { detail: 'fornecedor backend' } } });
    apiClient.post.mockRejectedValueOnce({ response: { data: { detail: 'create backend' } } });
    apiClient.put.mockRejectedValueOnce({ response: { data: { detail: 'update backend' } } });
    apiClient.delete.mockRejectedValueOnce({ response: { data: { detail: 'delete backend' } } });

    await expect(fornecedorService.getFornecedorById(4)).rejects.toEqual({
      detail: 'fornecedor backend',
    });
    await expect(fornecedorService.createFornecedor({ nome: 'Novo' })).rejects.toEqual({
      detail: 'create backend',
    });
    await expect(fornecedorService.updateFornecedor(4, { nome: 'Novo' })).rejects.toEqual({
      detail: 'update backend',
    });
    await expect(fornecedorService.deleteFornecedor(4)).rejects.toEqual({
      detail: 'delete backend',
    });
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

  test('setFornecedorMapping uses the default empty mapping payload when none is provided', async () => {
    apiClient.put.mockResolvedValueOnce({ data: { ok: true } });

    await expect(fornecedorService.setFornecedorMapping(8)).resolves.toEqual({ ok: true });

    expect(apiClient.put).toHaveBeenCalledWith('/fornecedores/8/mapping', {});
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

  test('previewCatalogo omits the optional fornecedor id when not provided', async () => {
    const file = new File(['conteudo'], 'catalogo.pdf', { type: 'application/pdf' });
    apiClient.post.mockResolvedValueOnce({
      data: {
        file_id: 91,
        headers: [],
        sample_rows: [],
        preview_images: [],
        num_pages: 1,
        table_pages: [],
      },
    });

    await fornecedorService.previewCatalogo(file, 5, 2);

    const [, formData] = apiClient.post.mock.calls[0];
    expect(formData.get('fornecedor_id')).toBeNull();
  });

  test('previewCatalogo and importCatalogo surface backend and generic failures', async () => {
    const file = new File(['conteudo'], 'catalogo.pdf', { type: 'application/pdf' });
    apiClient.post
      .mockRejectedValueOnce({ response: { data: { detail: 'preview backend' } } })
      .mockRejectedValueOnce(new Error('preview timeout'))
      .mockRejectedValueOnce(new Error('import config'));

    await expect(fornecedorService.previewCatalogo(file)).rejects.toEqual({
      detail: 'preview backend',
    });
    await expect(fornecedorService.previewCatalogo(file)).rejects.toThrow('preview timeout');
    await expect(fornecedorService.importCatalogo(9, file)).rejects.toThrow('import config');
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

  test('catalog import maintenance endpoints surface request and generic failures', async () => {
    apiClient.get
      .mockRejectedValueOnce({ request: {} })
      .mockRejectedValueOnce(new Error('status timeout'))
      .mockRejectedValueOnce(new Error('result timeout'));
    apiClient.delete.mockRejectedValueOnce(new Error('delete timeout'));
    apiClient.post.mockRejectedValueOnce(new Error('reprocess timeout'));

    await expect(fornecedorService.getCatalogImportFiles()).rejects.toThrow(
      /Nenhuma resposta do servidor ao buscar arquivos de importação/i
    );
    await expect(fornecedorService.deleteCatalogFile(8)).rejects.toThrow('delete timeout');
    await expect(fornecedorService.reprocessCatalogFile(8)).rejects.toThrow('reprocess timeout');
    await expect(fornecedorService.getImportacaoStatus(8)).rejects.toThrow('status timeout');
    await expect(fornecedorService.getImportacaoResult(8)).rejects.toThrow('result timeout');
  });

  test('catalog import maintenance endpoints cover remaining backend and generic branches', async () => {
    apiClient.get.mockRejectedValueOnce({});

    await expect(fornecedorService.getCatalogImportFiles()).rejects.toThrow(
      /Erro ao configurar requisi.*arquivos de importa/i
    );

    apiClient.post.mockRejectedValueOnce({ response: { data: { detail: 'reprocess backend' } } });
    await expect(fornecedorService.reprocessCatalogFile(8)).rejects.toEqual({
      detail: 'reprocess backend',
    });
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

  test('getImportacaoResult uses the default processing detail when the backend omits it', async () => {
    apiClient.get.mockResolvedValueOnce({
      status: 202,
      data: { status: 'QUEUED' },
    });

    await expect(fornecedorService.getImportacaoResult(13)).resolves.toEqual(
      expect.objectContaining({
        ready: false,
        status: 'QUEUED',
        detail: expect.stringMatching(/Resultado final ainda n.o dispon.vel/i),
      })
    );
  });

  test('getImportacaoResult falls back to PROCESSING when the backend status is blank', async () => {
    apiClient.get.mockResolvedValueOnce({
      status: 202,
      data: { status: '   ', detail: '' },
    });

    await expect(fornecedorService.getImportacaoResult(14)).resolves.toEqual({
      ready: false,
      status: 'PROCESSING',
      detail: 'Resultado final ainda não disponível. Continue monitorando o status.',
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

  test('upload and pdf preview surface generic failures', async () => {
    const file = new File(['conteudo'], 'catalogo.pdf', { type: 'application/pdf' });
    apiClient.post
      .mockRejectedValueOnce(new Error('upload timeout'))
      .mockRejectedValueOnce(new Error('pdf timeout'));

    await expect(fornecedorService.uploadForPagePreview(file, 3)).rejects.toThrow(
      'upload timeout'
    );
    await expect(fornecedorService.getPdfPreview(file, 3)).rejects.toThrow('pdf timeout');
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

  test('mapping, progress and commit endpoints surface generic failures', async () => {
    apiClient.get
      .mockRejectedValueOnce(new Error('page timeout'))
      .mockRejectedValueOnce(new Error('progress timeout'))
      .mockRejectedValueOnce(new Error('review timeout'));
    apiClient.post
      .mockRejectedValueOnce(new Error('process timeout'))
      .mockRejectedValueOnce(new Error('commit timeout'));

    await expect(fornecedorService.fetchPageDataForMapping(90, 4)).rejects.toThrow('page timeout');
    await expect(fornecedorService.startFullProcess({ file_id: 90 })).rejects.toThrow(
      'process timeout'
    );
    await expect(fornecedorService.getImportProgress('job-1')).rejects.toThrow(
      'progress timeout'
    );
    await expect(fornecedorService.getReviewData('job-1')).rejects.toThrow('review timeout');
    await expect(fornecedorService.commitImport('job-1')).rejects.toThrow('commit timeout');
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

  test('catalog helpers rethrow backend payloads when the API returns structured errors', async () => {
    const file = new File(['conteudo'], 'catalogo.pdf', { type: 'application/pdf' });

    apiClient.put
      .mockRejectedValueOnce({ response: { data: { detail: 'mapping backend' } } });
    apiClient.post
      .mockRejectedValueOnce({ response: { data: { detail: 'import backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'upload backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'pdf backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'process backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'region backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'bulk backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'produto backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'commit backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'final backend' } } });
    apiClient.get
      .mockRejectedValueOnce({ response: { data: { detail: 'files backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'status backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'page backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'progress backend' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'review backend' } } });
    apiClient.delete.mockRejectedValueOnce({ response: { data: { detail: 'delete backend' } } });

    await expect(fornecedorService.setFornecedorMapping(7, {})).rejects.toEqual({
      detail: 'mapping backend',
    });
    await expect(fornecedorService.importCatalogo(9, file)).rejects.toEqual({
      detail: 'import backend',
    });
    await expect(fornecedorService.getCatalogImportFiles()).rejects.toEqual({
      detail: 'files backend',
    });
    await expect(fornecedorService.deleteCatalogFile(8)).rejects.toEqual({
      detail: 'delete backend',
    });
    await expect(fornecedorService.getImportacaoStatus(8)).rejects.toEqual({
      detail: 'status backend',
    });
    await expect(fornecedorService.uploadForPagePreview(file, 3)).rejects.toEqual({
      detail: 'upload backend',
    });
    await expect(fornecedorService.getPdfPreview(file, 3)).rejects.toEqual({
      detail: 'pdf backend',
    });
    await expect(fornecedorService.fetchPageDataForMapping(90, 4)).rejects.toEqual({
      detail: 'page backend',
    });
    await expect(fornecedorService.startFullProcess({ file_id: 90 })).rejects.toEqual({
      detail: 'process backend',
    });
    await expect(fornecedorService.getImportProgress('job-1')).rejects.toEqual({
      detail: 'progress backend',
    });
    await expect(
      fornecedorService.selecionarRegiao({
        fileId: 1,
        pageNumber: 2,
        bbox: { x: 1, y: 2 },
      })
    ).rejects.toEqual({ detail: 'region backend' });
    await expect(
      fornecedorService.extractRegionBulk({
        fileId: 1,
        bbox: { x: 3, y: 4 },
      })
    ).rejects.toEqual({ detail: 'bulk backend' });
    await expect(
      fornecedorService.selecionarRegiaoProduto({
        fileId: 1,
        pageNumber: 4,
        bbox: { x: 5, y: 6 },
      })
    ).rejects.toEqual({ detail: 'produto backend' });
    await expect(fornecedorService.getReviewData('job-1')).rejects.toEqual({
      detail: 'review backend',
    });
    await expect(fornecedorService.commitImport('job-1')).rejects.toEqual({
      detail: 'commit backend',
    });
    await expect(
      fornecedorService.finalizarImportacaoCatalogo({
        fileId: 44,
        productTypeId: 7,
        fornecedorId: 8,
        extractionMode: 'manual',
      })
    ).rejects.toEqual({ detail: 'final backend' });
  });

  test('region selection and finalization endpoints surface generic failures', async () => {
    apiClient.post
      .mockRejectedValueOnce(new Error('region timeout'))
      .mockRejectedValueOnce(new Error('bulk timeout'))
      .mockRejectedValueOnce(new Error('produto timeout'))
      .mockRejectedValueOnce(new Error('final timeout'));

    await expect(
      fornecedorService.selecionarRegiao({
        fileId: 1,
        pageNumber: 2,
        bbox: { x: 1, y: 2 },
      })
    ).rejects.toThrow('region timeout');
    await expect(
      fornecedorService.extractRegionBulk({
        fileId: 1,
        bbox: { x: 3, y: 4 },
      })
    ).rejects.toThrow('bulk timeout');
    await expect(
      fornecedorService.selecionarRegiaoProduto({
        fileId: 1,
        pageNumber: 4,
        bbox: { x: 5, y: 6 },
      })
    ).rejects.toThrow('produto timeout');
    await expect(
      fornecedorService.finalizarImportacaoCatalogo({
        fileId: 44,
        productTypeId: 7,
        fornecedorId: 8,
      })
    ).rejects.toThrow('final timeout');
  });
});
