import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportCatalogWizard from '../ImportCatalogWizard.jsx';

jest.mock('pdfjs-dist/legacy/build/pdf.worker.js?url', () => 'worker-src-stub', { virtual: true });
jest.mock(
  'pdfjs-dist/legacy/build/pdf',
  () => ({
    GlobalWorkerOptions: { workerSrc: '' },
    getDocument: jest.fn(() => ({
      promise: Promise.resolve({
        getPage: jest.fn(() =>
          Promise.resolve({
            getViewport: () => ({ width: 100, height: 100 }),
            render: () => ({ promise: Promise.resolve() }),
          })
        ),
      }),
    })),
  }),
  { virtual: true }
);

jest.mock('../../../services/productTypeService', () => ({
  __esModule: true,
  default: {
    getProductTypes: jest.fn(() => Promise.resolve({ items: [] })),
    getProductTypeDetails: jest.fn(() => Promise.resolve({ attribute_templates: [] })),
  },
}));

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  previewCatalogo: jest.fn(),
  selecionarRegiaoProduto: jest.fn(),
  finalizarImportacaoCatalogo: jest.fn(),
  getImportacaoStatus: jest.fn(),
  getImportacaoResult: jest.fn(),
  setFornecedorMapping: jest.fn(),
}));

jest.mock('../../common/Modal.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, title, children }) =>
    isOpen ? (
      <div data-testid={`modal-${title || 'sem-titulo'}`}>
        {title ? <h2>{title}</h2> : null}
        {children}
      </div>
    ) : null,
}));

jest.mock('../../common/PdfRegionSelector.jsx', () => ({
  __esModule: true,
  default: ({ onSelect, initialPage, initialApplyAll }) => (
    <div>
      <p data-testid="pdf-region-selector">{`pagina-${initialPage}`}</p>
      <button
        type="button"
        onClick={() =>
          onSelect({
            page: initialPage,
            bbox: { x: 10, y: 20, width: 30, height: 40 },
            bboxNorm: { x: 0.1, y: 0.2, width: 0.3, height: 0.4 },
            canvasWidth: 1000,
            canvasHeight: 800,
            applyAllPages: initialApplyAll,
          })
        }
      >
        Confirmar regiao
      </button>
    </div>
  ),
}));

import * as fornecedorService from '../../../services/fornecedorService';
import productTypeService from '../../../services/productTypeService';

describe('ImportCatalogWizard', () => {
  let consoleErrorSpy;
  let consoleWarnSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  const createPdfFile = () => {
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    Object.defineProperty(file, 'arrayBuffer', {
      value: jest.fn(() => Promise.resolve(new ArrayBuffer(8))),
    });
    return file;
  };

  const uploadAndGeneratePreview = async () => {
    const fileInput = document.querySelector('input[type="file"]');
    const file = createPdfFile();
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));
    return file;
  };

  test('generates preview', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 1,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));

    await screen.findByRole('img', { name: /1/ });
    expect(fornecedorService.previewCatalogo).toHaveBeenCalledWith(file, 15, 1, 1);
    expect(screen.getByText(/Escopo atual:/i)).toHaveTextContent(/somente p[aá]gina 1/i);
  });

  test('starts import with selected page by default', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    productTypeService.getProductTypeDetails.mockResolvedValue({ attribute_templates: [] });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 1,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 231,
      tablePages: [],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 1,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'IMPORTED',
      pages_processed: 231,
      total_pages: 231,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      stats: { produtos_criados: 1, produtos_atualizados: 0, erros: 0, pages_processed: 231, pages_total: 231 },
      created: [],
      updated: [],
      errors: [],
      log: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));
    await screen.findByRole('img', { name: /1/ });

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByText('Iniciar Processamento'));

    await waitFor(() => {
        expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
          expect.objectContaining({
            fileId: 1,
            productTypeId: 4,
            fornecedorId: 1,
            pages: [1],
            extractionMode: 'ocr',
          })
        );
      });
  });

  test('starts import with IA extraction mode when selected', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    productTypeService.getProductTypeDetails.mockResolvedValue({ attribute_templates: [] });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 1,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 2,
      tablePages: [],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 1,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'IMPORTED',
      pages_processed: 2,
      total_pages: 2,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      stats: { produtos_criados: 1, produtos_atualizados: 0, erros: 0, pages_processed: 2, pages_total: 2 },
      created: [],
      updated: [],
      errors: [],
      log: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));
    await screen.findByRole('img', { name: /1/ });

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /modo de extracao/i }), 'ia');
    await userEvent.click(screen.getByText('Iniciar Processamento'));

    await waitFor(() => {
      expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
        expect.objectContaining({
          extractionMode: 'ia',
        })
      );
    });
  });

  test('waits for result_ready before fetching final result', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    productTypeService.getProductTypeDetails.mockResolvedValue({ attribute_templates: [] });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 1,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 231,
      tablePages: [],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 1,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      result_ready: true,
      pages_processed: 231,
      total_pages: 231,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'DONE',
      result_ready: false,
      pages_processed: 231,
      total_pages: 231,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      ready: true,
      stats: {
        produtos_criados: 3,
        produtos_atualizados: 1,
        erros: 0,
        pages_processed: 231,
        pages_total: 231,
      },
      created: [],
      updated: [],
      errors: [],
      log: ['ok'],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));
    await screen.findByRole('img', { name: /1/ });

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByText('Iniciar Processamento'));

    await waitFor(
      () => {
        expect(screen.getByText(/Criados: 3/i)).toBeInTheDocument();
      },
      { timeout: 6000 }
    );

    expect(fornecedorService.getImportacaoResult.mock.calls.length).toBeGreaterThanOrEqual(1);
  }, 15000);

  test('shows preview error returned by backend payload', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      error: 'Preview invalido para este arquivo.',
      fileId: null,
      previewImages: [],
      numPages: 0,
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();

    expect(
      await screen.findByText('Preview invalido para este arquivo.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/Passo 2:/i)).not.toBeInTheDocument();
  });

  test('shows preview error when preview request throws', async () => {
    fornecedorService.previewCatalogo.mockRejectedValue(new Error('Falha remota no preview'));

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();

    expect(await screen.findByText('Falha remota no preview')).toBeInTheDocument();
  });

  test('keeps manual mapping even when saving supplier mapping fails', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 8,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Filtro de oleo' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.setFornecedorMapping.mockRejectedValue(new Error('falha ao salvar'));

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Pr[ée]via das colunas detectadas/i);
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');

    const startButton = screen.getByRole('button', { name: /Iniciar Processamento/i });
    expect(startButton).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: /Definir mapeamento/i }));
    await screen.findByText('Mapear Colunas');

    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: /Campo para coluna titulo_bruto/i }),
      'auto:sku_nome'
    );
    await userEvent.click(screen.getByRole('button', { name: /Confirmar mapeamento/i }));

    await waitFor(() => {
      expect(fornecedorService.setFornecedorMapping).toHaveBeenCalledWith(1, {
        titulo_bruto: 'auto:sku_nome',
      });
    });
    expect(startButton).toBeEnabled();
  });

  test('extracts a selected region from a chosen preview page and opens mapping modal', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 13,
      headers: null,
      sampleRows: null,
      previewImages: [
        { page: 1, image: 'data:image/png;base64,abc' },
        { page: 2, image: 'data:image/png;base64,def' },
      ],
      numPages: 2,
      tablePages: [1, 2],
    });
    fornecedorService.selecionarRegiaoProduto.mockResolvedValue({
      preview_headers: ['sku', 'descricao'],
      preview_rows: [{ sku: 'SKU-1', descricao: 'Compressor premium' }],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Pr[ée]via de p[áa]ginas/i);

    await userEvent.click(screen.getByRole('button', { name: /Selecionar regi/i }));
    await userEvent.click(screen.getByRole('button', { name: /P.*2/i }));
    await screen.findByTestId('pdf-region-selector');
    await userEvent.click(screen.getByRole('button', { name: /Confirmar regiao/i }));

    await waitFor(() => {
      expect(fornecedorService.selecionarRegiaoProduto).toHaveBeenCalledWith(
        expect.objectContaining({
          fileId: 13,
          pageNumber: 2,
          bboxNorm: { x: 0.1, y: 0.2, width: 0.3, height: 0.4 },
        })
      );
    });

    expect((await screen.findAllByText('Compressor premium')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Mapear Colunas')).toBeInTheDocument();
  });

  test('builds region preview from extracted products when preview rows are unavailable', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 21,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.selecionarRegiaoProduto.mockResolvedValue({
      produtos: [{ codigo: 'A1', nome: 'Filtro de cabine' }],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Pr[ée]via de p[áa]ginas/i);
    await userEvent.click(screen.getByRole('button', { name: /Selecionar regi/i }));
    await screen.findByTestId('pdf-region-selector');
    await userEvent.click(screen.getByRole('button', { name: /Confirmar regiao/i }));

    expect((await screen.findAllByText('Filtro de cabine')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('codigo').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('nome').length).toBeGreaterThanOrEqual(1);
  });

  test('shows empty and failed region extraction feedback', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 34,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Pr[ée]via de p[áa]ginas/i);

    fornecedorService.selecionarRegiaoProduto.mockResolvedValueOnce({});
    await userEvent.click(screen.getByRole('button', { name: /Selecionar regi/i }));
    await screen.findByTestId('pdf-region-selector');
    await userEvent.click(screen.getByRole('button', { name: /Confirmar regiao/i }));
    expect(await screen.findByText('col_0')).toBeInTheDocument();
    expect(screen.queryByText('Mapear Colunas')).not.toBeInTheDocument();

    fornecedorService.selecionarRegiaoProduto.mockRejectedValueOnce({
      detail: 'Falha ao extrair regiao da pagina.',
    });
    await userEvent.click(screen.getByRole('button', { name: /Selecionar regi/i }));
    await screen.findByTestId('pdf-region-selector');
    await userEvent.click(screen.getByRole('button', { name: /Confirmar regiao/i }));
    expect(await screen.findByText('Falha ao extrair regiao da pagina.')).toBeInTheDocument();
  });

  test('returns to preview with an error when processing startup fails', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 55,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'PROCESSING',
      pages_processed: 0,
      total_pages: 1,
    });
    fornecedorService.finalizarImportacaoCatalogo.mockRejectedValue(new Error('Falha ao iniciar processamento.'));

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByRole('img', { name: /1/ });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    expect(await screen.findByText('Falha ao iniciar processamento.')).toBeInTheDocument();
    expect(screen.getByText(/Passo 2: Revisar e mapear dados/i)).toBeInTheDocument();
  });

  test('stops processing when status polling fails', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 89,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 89,
    });
    fornecedorService.getImportacaoStatus.mockRejectedValue(new Error('Falha ao consultar status da importacao.'));

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByRole('img', { name: /1/ });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    expect(
      await screen.findByText('Falha ao consultar status da importacao.')
    ).toBeInTheDocument();
  });

  test('retries final result fetching when backend still reports processing', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 144,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 144,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      result_ready: true,
      pages_processed: 1,
      total_pages: 1,
    });
    fornecedorService.getImportacaoResult
      .mockRejectedValueOnce(new Error('still processing'))
      .mockResolvedValueOnce({
        stats: {
          produtos_criados: 2,
          produtos_atualizados: 1,
          erros: 0,
          pages_processed: 1,
          pages_total: 1,
        },
        created: [],
        updated: [],
        errors: [],
        log: ['ok'],
      });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByRole('img', { name: /1/ });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    await waitFor(
      () => {
        expect(screen.getByText(/Criados: 2/i)).toBeInTheDocument();
      },
      { timeout: 7000 }
    );
    expect(fornecedorService.getImportacaoResult).toHaveBeenCalledTimes(2);
  }, 15000);
});
