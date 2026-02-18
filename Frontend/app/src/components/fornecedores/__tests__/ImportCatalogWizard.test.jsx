import { render, screen } from '@testing-library/react';
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
          }),
        ),
      }),
    })),
  }),
  { virtual: true },
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
        fornecedor={{ id: 1 }}
        onClose={() => {}}
        isOpen
      />,
    );

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));

    await screen.findByRole('img', { name: /1/ });
    expect(fornecedorService.previewCatalogo).toHaveBeenCalledWith(file, 15, 1, 1);
  });
});
