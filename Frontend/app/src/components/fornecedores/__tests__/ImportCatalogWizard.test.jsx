import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportCatalogWizard from '../ImportCatalogWizard.jsx';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

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
  default: ({ isOpen, title, children, onClose }) =>
    isOpen ? (
      <div data-testid={`modal-${title || 'sem-titulo'}`}>
        {title ? <h2>{title}</h2> : null}
        <button type="button" onClick={() => onClose?.()}>
          {`fechar-${title || 'sem-titulo'}`}
        </button>
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
    jest.useRealTimers();
  });

  const createPdfFile = () => {
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    Object.defineProperty(file, 'arrayBuffer', {
      value: jest.fn(() => Promise.resolve(new ArrayBuffer(8))),
    });
    return file;
  };

  const selectPreviewMode = async (interaction = userEvent) => {
    await interaction.click(screen.getByRole('button', { name: /OCR/i }));
  };

  const uploadAndGeneratePreview = async (interaction = userEvent) => {
    const fileInput = document.querySelector('input[type="file"]');
    const file = createPdfFile();
    await interaction.upload(fileInput, file);
    await selectPreviewMode(interaction);
    await interaction.click(screen.getByText('Gerar Preview'));
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

    const file = await uploadAndGeneratePreview();

    await screen.findByRole('img', { name: /1/ });
    expect(fornecedorService.previewCatalogo).toHaveBeenCalledWith(file, 15, 1, 1);
    expect(screen.getByText(/Escopo atual:/i)).toHaveTextContent(/somente página 1/i);
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

    await uploadAndGeneratePreview();
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

    // Select IA Local mode on step 1 (the mode cards are shown before preview)
    await userEvent.click(screen.getByRole('button', { name: /IA Local/i }));
    // Product type selector now visible for direct modes
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByText('Iniciar Importação'));

    await waitFor(() => {
      expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
        expect.objectContaining({
          extractionMode: 'ia',
        })
      );
    });
  });

  test('keeps processing disabled until a product type is selected', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 2,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Filtro' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { titulo_bruto: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText('Filtro');

    const startButton = screen.getByRole('button', { name: /Iniciar Processamento/i });
    expect(startButton).toBeDisabled();
    expect(
      screen.getByText(/Selecione o tipo de produto para habilitar a importação/i)
    ).toBeInTheDocument();
    expect(fornecedorService.finalizarImportacaoCatalogo).not.toHaveBeenCalled();
  });

  test('uses all pages and clamps the selected region page when apply-all is enabled', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    productTypeService.getProductTypeDetails.mockResolvedValue({ attribute_templates: [] });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 3,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Filtro premium' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 4,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 3,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'IMPORTED',
      pages_processed: 4,
      total_pages: 4,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      stats: { produtos_criados: 1, produtos_atualizados: 0, erros: 0, pages_processed: 4, pages_total: 4 },
      created: [],
      updated: [],
      errors: [],
      log: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { titulo_bruto: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Colunas detectadas/i);
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    fireEvent.change(screen.getByLabelText(/Página para seleção/i), { target: { value: '0' } });
    expect(screen.getByLabelText(/Página para seleção/i)).toHaveValue(1);

    await userEvent.click(screen.getByLabelText(/Aplicar região em todas as páginas/i));
    expect(screen.getByText(/Escopo atual:/i)).toHaveTextContent(/todas as p.ginas do PDF/i);
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    await waitFor(() => {
      expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
        expect.objectContaining({
          pages: null,
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

    await uploadAndGeneratePreview();
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

  test('falls back to the default preview error when the backend throws an empty payload', async () => {
    fornecedorService.previewCatalogo.mockRejectedValue({});

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();

    expect(await screen.findByText('Falha ao gerar preview.')).toBeInTheDocument();
  });

  test('shows unsupported preview warning when backend returns no headers and no images', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 77,
      headers: null,
      sampleRows: null,
      previewImages: [],
      numPages: 1,
      tablePages: [],
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
      await screen.findByText('Nenhum preview disponível. Verifique se o arquivo é suportado.')
    ).toBeInTheDocument();
  });

  test('skips preview pages without image data and allows modal close callbacks', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 81,
      headers: ['titulo'],
      sampleRows: [{ titulo: 'Filtro' }],
      previewImages: ['   ', { page: 2, image: 'data:image/png;base64,xyz' }],
      numPages: 2,
      tablePages: [1, 2],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { titulo: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    expect(await screen.findAllByRole('img', { name: /2/ })).toHaveLength(2);
    expect(screen.queryByRole('img', { name: /1/ })).not.toBeInTheDocument();

    expect(screen.getByTestId(/modal-Escolha a p.+gina/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /P.*1/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /P.*2/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /fechar-Escolha a p.+gina/i }));
    expect(screen.queryByTestId(/modal-Escolha a p.+gina/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Definir mapeamento/i }));
    expect(await screen.findByText('Mapear Colunas')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /fechar-Mapear Colunas/i }));
    expect(screen.queryByText('Mapear Colunas')).not.toBeInTheDocument();
  });

  test('opens manual mapping with fallback headers when there are no extracted rows', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 79,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByRole('img', { name: /1/ });

    await userEvent.click(screen.getByRole('button', { name: /Mapear manualmente/i }));

    expect(await screen.findByText('Mapear Colunas')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /Campo para coluna col_0/i })).toBeInTheDocument();
  });

  test('normalizes raw preview image strings and respects preview page inputs', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 78,
      headers: null,
      sampleRows: null,
      previewImages: ['raw-base64-image'],
      numPages: 3,
      tablePages: [3],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 9, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = createPdfFile();
    await userEvent.upload(fileInput, file);
    await selectPreviewMode();
    fireEvent.change(screen.getByLabelText(/Página inicial/i), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText(/Quantidade de páginas/i), { target: { value: '1' } });
    await userEvent.click(screen.getByText('Gerar Preview'));

    const image = await screen.findByRole('img', { name: /3/ });
    expect(image).toHaveAttribute('src', 'data:image/png;base64,raw-base64-image');
    expect(fornecedorService.previewCatalogo).toHaveBeenCalledWith(expect.any(File), 1, 3, 9);
  });

  test('sanitizes empty page inputs and opens the region selector without preview images', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 84,
      headers: ['titulo'],
      sampleRows: [{ titulo: 'Filtro da cabine' }],
      previewImages: [],
      numPages: 0,
      tablePages: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = createPdfFile();
    await userEvent.upload(fileInput, file);
    await selectPreviewMode();
    fireEvent.change(screen.getByLabelText(/Página inicial/i), { target: { value: '' } });
    fireEvent.change(screen.getByLabelText(/Quantidade de páginas/i), { target: { value: '' } });
    await userEvent.click(screen.getByText('Gerar Preview'));

    expect(await screen.findByText('Filtro da cabine')).toBeInTheDocument();
    expect(fornecedorService.previewCatalogo).toHaveBeenCalledWith(expect.any(File), 1, 1, 1);

    fireEvent.change(screen.getByLabelText(/Página para seleção/i), { target: { value: '' } });
    await userEvent.click(screen.getByRole('button', { name: /Selecionar regi/i }));
    expect(await screen.findByTestId('pdf-region-selector')).toHaveTextContent('pagina-1');
  });

  test('serializes object detail when preview request fails with structured payload', async () => {
    fornecedorService.previewCatalogo.mockRejectedValue({
      detail: { reason: 'layout_invalido', page: 4 },
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
      await screen.findByText('{"reason":"layout_invalido","page":4}')
    ).toBeInTheDocument();
  });

  test('keeps the product type selector usable when loading types fails', async () => {
    productTypeService.getProductTypes.mockRejectedValueOnce(new Error('falha tipos'));
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 80,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByRole('img', { name: /1/ });

    const productTypeSelect = screen.getByRole('combobox', { name: /tipo de produto/i });
    expect(productTypeSelect).toBeInTheDocument();
    expect(screen.getAllByRole('option', { name: /Selecione/i })).toHaveLength(1);
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Erro ao carregar tipos de produto:',
      expect.any(Error)
    );
  });

  test('loads attribute options for the selected product type and skips invalid ids', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [
        { id: null, friendly_name: 'Ignorar' },
        { id: 7, friendly_name: 'Linha pesada' },
      ],
    });
    productTypeService.getProductTypeDetails.mockResolvedValue({
      attribute_templates: [{ attribute_key: 'cor', label: 'Cor' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 82,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Cubo de roda' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { titulo_bruto: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText('Cubo de roda');

    const productTypeSelect = screen.getByRole('combobox', { name: /tipo de produto/i });
    expect(screen.queryByRole('option', { name: 'Ignorar' })).not.toBeInTheDocument();

    await userEvent.selectOptions(productTypeSelect, '7');
    await userEvent.click(screen.getByRole('button', { name: /Definir mapeamento/i }));

    expect(
      await screen.findByRole('combobox', { name: /Campo para coluna titulo_bruto/i })
    ).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Atributo: Cor/i })).toBeInTheDocument();
  });

  test('falls back to base field options when loading product type attributes fails', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    productTypeService.getProductTypeDetails.mockRejectedValueOnce(new Error('falha attrs'));
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 83,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Compressor' }],
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
    await screen.findByText(/Colunas detectadas/i);
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByRole('button', { name: /Definir mapeamento/i }));

    expect(await screen.findByText('Mapear Colunas')).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Atributo: Compatibilidade/i })).not.toBeInTheDocument();
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      'Falha ao carregar atributos do tipo de produto:',
      expect.any(Error)
    );
  });

  test('resets the wizard state when closing and reopening the modal', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 81,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [],
    });

    const { rerender } = render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    expect(await screen.findByRole('img', { name: /1/ })).toBeInTheDocument();

    rerender(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen={false}
      />
    );

    rerender(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    expect(screen.getByText('Passo 1: Enviar catálogo')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: /1/ })).not.toBeInTheDocument();
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
    await screen.findByText(/Colunas detectadas/i);
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

  test('saves supplier mapping successfully when mapping confirmation succeeds', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 82,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Compressor de ar' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.setFornecedorMapping.mockResolvedValue({ ok: true });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Colunas detectadas/i);

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
    expect(screen.queryByText('Mapear Colunas')).not.toBeInTheDocument();
  });

  test('keeps local mapping when the supplier has no id to persist defaults', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 183,
      headers: ['titulo_bruto'],
      sampleRows: [{ titulo_bruto: 'Compressor axial' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ default_column_mapping: {} }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText(/Colunas detectadas/i);
    await userEvent.click(screen.getByRole('button', { name: /Definir mapeamento/i }));
    await screen.findByText('Mapear Colunas');
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: /Campo para coluna titulo_bruto/i }),
      'auto:sku_nome'
    );
    await userEvent.click(screen.getByRole('button', { name: /Confirmar mapeamento/i }));

    expect(fornecedorService.setFornecedorMapping).not.toHaveBeenCalled();
    expect(screen.queryByText('Mapear Colunas')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Iniciar Processamento/i })).toBeDisabled();
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
    await screen.findByText(/Prévia de páginas/i);

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

  test('closes the region selector modal without selecting a region', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 83,
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
    await screen.findByRole('img', { name: /1/ });
    await userEvent.click(screen.getByRole('button', { name: /Selecionar regi/i }));
    expect(await screen.findByTestId(/modal-Selecione a regi/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /fechar-Selecione a regi/i }));
    expect(screen.queryByTestId(/modal-Selecione a regi/i)).not.toBeInTheDocument();
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
    await screen.findByText(/Prévia de páginas/i);
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
    await screen.findByText(/Prévia de páginas/i);

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
    expect(screen.getByText(/Revisar e mapear dados/i)).toBeInTheDocument();
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

  test('surfaces a hard final-result fetch error instead of retrying forever', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 177,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 177,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      result_ready: true,
      pages_processed: 1,
      total_pages: 1,
    });
    fornecedorService.getImportacaoResult.mockRejectedValueOnce({
      detail: 'erro fatal no consolidado',
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

    expect(await screen.findByText('erro fatal no consolidado')).toBeInTheDocument();
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Erro ao obter resultado final:',
      expect.any(Object)
    );
  });

  test('shows a timeout when processing stalls without progress for too long', async () => {
    jest.useFakeTimers();
    const localUser = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 190,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 190,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'PROCESSING',
      pages_processed: 0,
      total_pages: 1,
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview(localUser);
    await screen.findByRole('img', { name: /1/ });
    await localUser.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await localUser.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    for (let step = 0; step < 160; step += 1) {
      await jest.advanceTimersByTimeAsync(2000);
    }

    expect(
      (await screen.findAllByText(/Monitoramento encerrado por inatividade de progresso/i)).length
    ).toBeGreaterThan(0);
    expect(screen.getByText(/Tempo decorrido: 300s/i)).toBeInTheDocument();
    expect(fornecedorService.getImportacaoResult).not.toHaveBeenCalled();
  }, 20000);

  test('shows a timeout when the final result remains pending even after ready checks', async () => {
    jest.useFakeTimers();
    const localUser = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 191,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 191,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      result_ready: true,
      pages_processed: 1,
      total_pages: 1,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      ready: false,
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview(localUser);
    await screen.findByRole('img', { name: /1/ });
    await localUser.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await localUser.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    for (let step = 0; step < 35; step += 1) {
      await jest.advanceTimersByTimeAsync(2000);
    }

    expect(
      (await screen.findAllByText(/Resultado ainda pendente/i)).length
    ).toBeGreaterThan(0);
  }, 20000);

  test('shows a timeout message when the final result never becomes ready', async () => {
    jest.useFakeTimers();
    const localUser = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 188,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 188,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      result_ready: false,
      pages_processed: 1,
      total_pages: 1,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      ready: false,
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview(localUser);
    await screen.findByRole('img', { name: /1/ });
    await localUser.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await localUser.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    for (let step = 0; step < 30; step += 1) {
      await jest.advanceTimersByTimeAsync(2000);
    }

    expect(
      await screen.findByText(
        'Processamento concluído, mas o resultado final ainda não ficou disponível. Tente atualizar em instantes.'
      )
    ).toBeInTheDocument();
  }, 20000);

  test('renders detailed final result sections with normalized output strings', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 205,
      headers: ['meta'],
      sampleRows: [{ meta: { sku: 'ABC-1' } }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 205,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'PARTIAL',
      result_ready: true,
      pages_processed: 1,
      total_pages: 1,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      output: {
        status_label: 'Conclu?do com revis?o',
        headline: 'Relat?rio com n?o cr?ticos',
        pages: { progress_pct: 100 },
      },
      stats: {
        produtos_criados: 1,
        produtos_atualizados: 2,
        erros: 1,
        pages_processed: 1,
        pages_total: 1,
        ext: 'pdf',
        partial_success: true,
        descartes_nao_criticos: 3,
        qualidade_score_medio_aceitas: 0.91,
        qualidade_score_medio_quarentena: 0.42,
      },
      errors: [{ erro_processamento_pdf: 'Linha cr?tica' }],
      log: ['Importa??o conclu?da'],
      top_reasons: [{ reason: 'cat?logo sem sku', count: 2 }],
      quarantine_non_critical: [{ linha: 8, motivo: 'material ausente' }],
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { meta: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    expect(await screen.findByText('{"sku":"ABC-1"}')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    expect(await screen.findByText(/Conclu.do com revis.o/i)).toBeInTheDocument();
    expect(screen.getByText(/Relat.rio com n.o cr.ticos/i)).toBeInTheDocument();
    expect(screen.getByText(/Importa..o conclu.da com alertas/i)).toBeInTheDocument();
    expect(screen.getByText(/Progresso final: 100%/i)).toBeInTheDocument();
    expect(screen.getByText(/Qualidade m.dia \(aceitos\): 0.91/i)).toBeInTheDocument();
    expect(screen.getByText(/Qualidade m.dia \(quarentena\): 0.42/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Top motivos de erro/i));
    fireEvent.click(screen.getByText(/^Erros$/i));
    fireEvent.click(screen.getByText(/^Log$/i));
    fireEvent.click(screen.getByText(/Linhas em quarentena/i));

    expect(screen.getByText(/cat.logo sem sku/i)).toBeInTheDocument();
    expect(screen.getByText(/Linha cr.tica/i)).toBeInTheDocument();
    expect(screen.getByText(/material ausente/i)).toBeInTheDocument();
    expect(
      screen.getByText((content, element) =>
        element?.tagName.toLowerCase() === 'pre' && /Importa..o conclu.da/i.test(content)
      )
    ).toBeInTheDocument();
  });

  test('shows the failed-result message when the backend finishes with status FAILED', async () => {
    productTypeService.getProductTypes.mockResolvedValue({
      items: [{ id: 4, friendly_name: 'Automotivo' }],
    });
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 206,
      headers: ['titulo'],
      sampleRows: [{ titulo: 'Compressor' }],
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [1],
    });
    fornecedorService.finalizarImportacaoCatalogo.mockResolvedValue({
      status: 'PROCESSING',
      file_id: 206,
    });
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'FAILED',
      result_ready: true,
      pages_processed: 1,
      total_pages: 1,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      errors: [{ erro_processamento: 'Arquivo sem layout válido' }],
      stats: { pages_processed: 1, pages_total: 1 },
    });

    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { titulo: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    await screen.findByText('Compressor');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /tipo de produto/i }), '4');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Processamento/i }));

    expect(await screen.findByText(/Falha: Arquivo sem layout válido/i)).toBeInTheDocument();
  });
  test('ignores empty file selections without resetting the wizard state', async () => {
    render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [] },
    });

    expect(screen.queryByText(/Arquivo selecionado:/i)).not.toBeInTheDocument();
    expect(fornecedorService.previewCatalogo).not.toHaveBeenCalled();
  });

  test('preserves the current preview when rerendered with the same reset key', async () => {
    fornecedorService.previewCatalogo.mockResolvedValue({
      fileId: 91,
      headers: null,
      sampleRows: null,
      previewImages: [{ page: 1, image: 'data:image/png;base64,abc' }],
      numPages: 1,
      tablePages: [],
    });

    const { rerender } = render(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    await uploadAndGeneratePreview();
    expect(await screen.findByRole('img', { name: /1/ })).toBeInTheDocument();

    rerender(
      <ImportCatalogWizard
        fornecedor={{ id: 1, default_column_mapping: { col_0: 'auto:sku_nome' } }}
        onClose={() => {}}
        isOpen
      />
    );

    expect(screen.getByRole('img', { name: /1/ })).toBeInTheDocument();
    expect(screen.getByText(/Revisar e mapear dados/i)).toBeInTheDocument();
  });
});



