import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportCatalogWizard from '../ImportCatalogWizard.jsx';

jest.mock('../../../contexts/ProductTypeContext', () => ({
  useProductTypes: jest.fn(() => ({
    productTypes: [{ id: 1, friendly_name: 'Type A' }],
    isLoading: false,
  })),
  useProductTypes: () => ({
    productTypes: [{ id: 1, friendly_name: 'Tipo1', attribute_templates: [] }],
    addProductType: jest.fn(),
  }),
}));

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    previewCatalogo: jest.fn(() => Promise.resolve({
      fileId: 'f1',
      headers: ['Nome'],
      sampleRows: [{ Nome: 'Item' }],
      previewImages: ['abc'],
    })),
    finalizarImportacaoCatalogo: jest.fn(() => Promise.resolve({ success: true })),
  },
}));
import fornecedorService from '../../../services/fornecedorService';

beforeEach(() => {
  jest.clearAllMocks();
});

test('shows preview rows and sends productTypeId on confirm', async () => {
  render(<ImportCatalogWizard isOpen={true} onClose={() => {}} fornecedorId={1} />);
  const fileInput = document.querySelector('input[type="file"]');
  const file = new File(['a'], 'test.csv', { type: 'text/csv' });
  await userEvent.upload(fileInput, file);
  await userEvent.click(screen.getByText('Gerar Preview'));
  await userEvent.selectOptions(screen.getByRole('combobox'), '1');
  await userEvent.click(screen.getByText('Continuar'));
  expect(await screen.findByDisplayValue('Item')).toBeInTheDocument();
  await userEvent.click(screen.getByText('Confirmar Importação'));
  expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
    'f1',
    expect.any(Object),
    expect.any(Array),
    1,
  );
  expect(await screen.findByText('Item')).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText(/Tipo de Produto/i), '1');
  await userEvent.click(screen.getByText('Continuar'));
  await userEvent.type(screen.getAllByRole('textbox')[0], 'X');
  await userEvent.click(screen.getByText('Confirmar Importação'));
  expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith('f1', expect.any(Object), expect.any(Array), 1);
});

test('calls onClose after finishing import', async () => {
  const onClose = jest.fn();
  render(<ImportCatalogWizard isOpen={true} onClose={onClose} fornecedorId={1} />);
  const fileInput = document.querySelector('input[type="file"]');
  const file = new File(['a'], 'test.csv', { type: 'text/csv' });
  await userEvent.upload(fileInput, file);
  await userEvent.click(screen.getByText('Gerar Preview'));
  await userEvent.selectOptions(screen.getByRole('combobox'), '1');
  await userEvent.click(screen.getByText('Continuar'));
  await userEvent.click(await screen.findByText('Confirmar Importação'));
  await userEvent.selectOptions(await screen.findByLabelText(/Tipo de Produto/i), '1');
  await userEvent.click(screen.getByText('Continuar'));
  await userEvent.click(screen.getByText('Confirmar Importação'));
  await userEvent.click(screen.getByText('Fechar'));
  expect(onClose).toHaveBeenCalled();
});
