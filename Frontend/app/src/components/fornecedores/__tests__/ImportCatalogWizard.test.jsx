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

import * as fornecedorService from '../../../services/fornecedorService';
import productTypeService from '../../../services/productTypeService';

describe('ImportCatalogWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

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
});
