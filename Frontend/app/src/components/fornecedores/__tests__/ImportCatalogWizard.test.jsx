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
    1,
    expect.any(Object),
    expect.any(Array),
    1,
  );
  expect(await screen.findByText('Importação concluída com sucesso')).toBeInTheDocument();
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
  await userEvent.click(screen.getByText('Fechar'));
  expect(onClose).toHaveBeenCalled();
});

test('confirms import even when fileId is missing', async () => {
  fornecedorService.previewCatalogo.mockResolvedValueOnce({
    fileId: null,
    headers: ['Nome'],
    sampleRows: [{ Nome: 'Item' }],
    previewImages: [],
  });

  render(<ImportCatalogWizard isOpen={true} onClose={() => {}} fornecedorId={1} />);
  const fileInput = document.querySelector('input[type="file"]');
  const file = new File(['a'], 'test.csv', { type: 'text/csv' });
  await userEvent.upload(fileInput, file);
  await userEvent.click(screen.getByText('Gerar Preview'));
  await userEvent.selectOptions(screen.getByRole('combobox'), '1');
  await userEvent.click(screen.getByText('Continuar'));
  await userEvent.click(screen.getByText('Confirmar Importação'));
  expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
    null,
    1,
    expect.any(Object),
    expect.any(Array),
    1,
  );
});
