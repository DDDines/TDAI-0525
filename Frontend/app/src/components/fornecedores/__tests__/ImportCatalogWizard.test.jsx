import { render, screen, within, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportCatalogWizard from '../ImportCatalogWizard.jsx';

jest.setTimeout(30000);

global.URL.createObjectURL = jest.fn(() => 'blob:url');

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
      numPages: 2,
    })),
    selecionarRegiao: jest.fn(() => Promise.resolve({ produtos: [] })),
    finalizarImportacaoCatalogo: jest.fn(() => Promise.resolve({ status: 'PROCESSING', file_id: 'f1' })),
    getImportacaoStatus: jest.fn(() => Promise.resolve({ status: 'IMPORTED' })),
  },
}));
import fornecedorService from '../../../services/fornecedorService';

jest.mock('../../common/PdfRegionSelector.jsx', () => ({
  __esModule: true,
  default: ({ onSelect, initialPage }) => (
    <button onClick={() => onSelect({ page: initialPage, bbox: [0, 0, 10, 10] })}>
      Select Region
    </button>
  ),
}));

describe.skip('ImportCatalogWizard', () => {
beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

test.skip('region modal sends selected page', async () => {
  render(<ImportCatalogWizard isOpen={true} onClose={() => {}} fornecedorId={1} />);
  const fileInput = document.querySelector('input[type="file"]');
  const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
  await userEvent.upload(fileInput, file);
  await userEvent.click(screen.getByText('Gerar Preview'));
  const regionButton = await screen.findByText('Selecionar Região');
  await userEvent.click(regionButton);
  const modal = document.querySelector('.modal-content');
  await userEvent.click(within(modal).getByText('Próxima'));
  await userEvent.click(within(modal).getByText('Select Region'));
  expect(fornecedorService.selecionarRegiao).toHaveBeenCalledWith(
    'f1',
    2,
    [0, 0, 10, 10],
  );
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
  jest.runOnlyPendingTimers();
  expect(fornecedorService.finalizarImportacaoCatalogo).toHaveBeenCalledWith(
    'f1',
    1,
    expect.any(Object),
    1,
    expect.any(Set),
  );
  expect(fornecedorService.getImportacaoStatus).toHaveBeenCalled();
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
  jest.runOnlyPendingTimers();
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
    1,
    expect.any(Set),
  );
});


});

test.skip('region modal sends selected page', async () => {
test('sends only selected pages', async () => {
  fornecedorService.previewCatalogo.mockResolvedValueOnce({
    fileId: 'f1',
    headers: ['Nome'],
    sampleRows: [{ Nome: 'Item' }],
    previewImages: ['a', 'b'],
    numPages: 2,
  });
  render(<ImportCatalogWizard isOpen={true} onClose={() => {}} fornecedorId={1} />);
  const fileInput = document.querySelector('input[type="file"]');
  const file = new File(['a'], 'test.pdf', { type: 'application/pdf' });
  await userEvent.upload(fileInput, file);
  await userEvent.click(screen.getByText('Gerar Preview'));
  const btn = await screen.findByText('Selecionar Região');
  await userEvent.click(btn);
  const modal = document.querySelector('.modal-content');
  await userEvent.click(await within(modal).findByText('Próxima'));
  await userEvent.click(await within(modal).findByText('Select Region'));
  await waitFor(() =>
    expect(fornecedorService.selecionarRegiao).toHaveBeenCalled(),
  );
  const call = fornecedorService.selecionarRegiao.mock.calls[0];
  expect(call[0]).toBe('f1');
  expect(call[1]).toBe(2);
  await userEvent.click(screen.getByText('Próxima'));
  await userEvent.click(screen.getByRole('checkbox'));
  await userEvent.click(screen.getByText('Anterior'));
  await userEvent.selectOptions(screen.getByRole('combobox'), '1');
  await userEvent.click(screen.getByText('Continuar'));
  await userEvent.click(screen.getByText('Confirmar Importação'));
  const pages = fornecedorService.finalizarImportacaoCatalogo.mock.calls[0][5];
  expect(Array.from(pages)).toEqual([1]);
});
});
