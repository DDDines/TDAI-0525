import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import EditFornecedorModal from '../EditFornecedorModal.jsx';

jest.mock('../ImportCatalogWizard.jsx', () => () => <div>Wizard</div>);

jest.mock('../../../utils/backend.js', () => ({
  __esModule: true,
  default: () => 'http://backend',
  getBackendBaseUrl: () => 'http://backend'
}));

const filesMock = [
  { id: 1, original_filename: 'file1.csv', status: 'IMPORTED', created_at: '2024-01-01T00:00:00Z' }
];

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getCatalogImportFiles: jest.fn(() => Promise.resolve(filesMock)),
    deleteCatalogFile: jest.fn(() => Promise.resolve({})),
    reprocessCatalogFile: jest.fn(() => Promise.resolve({})),
  },
}));

import fornecedorService from '../../../services/fornecedorService';

test('loads and displays catalog files on Arquivos tab', async () => {
  render(
    <EditFornecedorModal
      isOpen={true}
      fornecedorData={{ id: 5, nome: 'Fornecedor X' }}
      onClose={() => {}}
      onSave={() => {}}
      isLoading={false}
    />
  );
  await userEvent.click(screen.getByText('Arquivos'));
  await waitFor(() => expect(fornecedorService.getCatalogImportFiles).toHaveBeenCalledWith({ fornecedor_id: 5 }));
  expect(await screen.findByText('file1.csv')).toBeInTheDocument();
});

test('calls delete and reprocess when buttons clicked', async () => {
  render(
    <EditFornecedorModal
      isOpen={true}
      fornecedorData={{ id: 5, nome: 'Fornecedor X' }}
      onClose={() => {}}
      onSave={() => {}}
      isLoading={false}
    />
  );
  await userEvent.click(screen.getByText('Arquivos'));
  const reprocessBtn = await screen.findByText('Reprocessar');
  const deleteBtn = await screen.findByText('Excluir');
  await userEvent.click(reprocessBtn);
  await userEvent.click(deleteBtn);
  expect(fornecedorService.reprocessCatalogFile).toHaveBeenCalledWith(1);
  expect(fornecedorService.deleteCatalogFile).toHaveBeenCalledWith(1);
});
