import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportCatalogWizard from '../ImportCatalogWizard.jsx';

jest.mock('pdfjs-dist/legacy/build/pdf.worker.js?url', () => 'worker-src-stub', { virtual: true });
jest.mock(
  'pdfjs-dist/legacy/build/pdf.js',
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

global.URL.createObjectURL = jest.fn(() => 'blob:url');

jest.mock('../../../contexts/ProductTypeContext', () => ({
  useProductTypes: () => ({
    productTypes: [],
    addProductType: jest.fn(),
  }),
}));

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    previewPdf: jest.fn(),
  },
}));
import fornecedorService from '../../../services/fornecedorService';

describe('ImportCatalogWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('generates preview and loads more pages', async () => {
    fornecedorService.previewPdf
      .mockResolvedValueOnce({ pages: ['a', 'b'], totalPages: 3 })
      .mockResolvedValueOnce({ pages: ['c'], totalPages: 3 });

    render(<ImportCatalogWizard onClose={() => {}} fornecedor={{ id: 1 }} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
    await userEvent.upload(fileInput, file);
    await userEvent.click(screen.getByText('Gerar Preview'));

    expect(fornecedorService.previewPdf).toHaveBeenCalledWith(1, file, 0, 20);
    await screen.findByAltText('Página 1');

    await userEvent.click(screen.getByText('Carregar mais páginas'));
    expect(fornecedorService.previewPdf).toHaveBeenLastCalledWith(1, file, 2, 20);
  });
});
