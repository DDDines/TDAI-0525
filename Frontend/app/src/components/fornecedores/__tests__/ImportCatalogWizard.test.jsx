import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/extend-expect';
import userEvent from '@testing-library/user-event';
import ImportCatalogWizard from '../ImportCatalogWizard.jsx';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    previewCatalogo: jest.fn(() => Promise.resolve({
      fileId: 'f1',
      headers: ['Nome'],
      sampleRows: [{ Nome: 'Item' }],
    })),
    finalizarImportacaoCatalogo: jest.fn(() => Promise.resolve({ success: true })),
  },
}));
import fornecedorService from '../../../services/fornecedorService';

beforeEach(() => {
  jest.clearAllMocks();
});

test('shows preview rows and sends fileId on confirm', async () => {
  render(<ImportCatalogWizard isOpen={true} onClose={() => {}} fornecedorId={1} />);
  const fileInput = document.querySelector('input[type="file"]');
  const file = new File(['a'], 'test.csv', { type: 'text/csv' });
  await userEvent.upload(fileInput, file);
  await userEvent.click(screen.getByText('Gerar Preview'));
  expect(await screen.findByDisplayValue('Item')).toBeInTheDocument();
  await userEvent.click(screen.getByText('Confirmar Importação'));
  expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith('f1', expect.any(Object), expect.any(Array));
});
