import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import EditFornecedorModal from '../EditFornecedorModal.jsx';
import fornecedorService from '../../../services/fornecedorService';
import { showErrorToast, showWarningToast } from '../../../utils/notifications';

const filesMock = [
  { id: 1, original_filename: 'file1.csv', status: 'IMPORTED', created_at: '2024-01-01T00:00:00Z' },
];

jest.mock('../ImportCatalogWizard.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, onClose, fornecedor }) => (
    <div data-testid="wizard-state" data-open={String(isOpen)}>
      <span>{fornecedor?.nome || 'sem-fornecedor'}</span>
      <button onClick={onClose}>close-wizard</button>
    </div>
  ),
}));

jest.mock('../CatalogFileList.jsx', () => ({
  __esModule: true,
  default: ({ files, onReprocess, onDelete }) => (
    <div>
      <div data-testid="catalog-file-names">
        {files.map((file) => file.original_filename).join(',')}
      </div>
      <button onClick={() => onReprocess(files[0]?.id)}>reprocess-first</button>
      <button onClick={() => onDelete(files[0]?.id)}>delete-first</button>
    </div>
  ),
}));

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getCatalogImportFiles: jest.fn(),
    deleteCatalogFile: jest.fn(),
    reprocessCatalogFile: jest.fn(),
  },
}));

jest.mock('../../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

describe('EditFornecedorModal', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    fornecedorService.getCatalogImportFiles.mockResolvedValue({ items: filesMock });
    fornecedorService.deleteCatalogFile.mockResolvedValue({});
    fornecedorService.reprocessCatalogFile.mockResolvedValue({});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('returns null when closed or missing supplier data', () => {
    const { container, rerender } = render(
      <EditFornecedorModal
        isOpen={false}
        fornecedorData={{ id: 5, nome: 'Fornecedor X' }}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={false}
      />
    );

    expect(container).toBeEmptyDOMElement();

    rerender(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={null}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={false}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });

  test('loads supplier info, updates fields and normalizes url before saving', async () => {
    const onSave = jest.fn();
    const onClose = jest.fn();
    const { rerender } = render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X', site_url: 'https://fornecedor.test' }}
        onClose={onClose}
        onSave={onSave}
        isLoading={false}
      />
    );

    expect(screen.getByLabelText('Nome*')).toHaveValue('Fornecedor X');
    expect(screen.getByLabelText('Site URL')).toHaveValue('https://fornecedor.test');

    rerender(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 9, nome: 'Fornecedor Y', site_url: '' }}
        onClose={onClose}
        onSave={onSave}
        isLoading={false}
      />
    );

    expect(screen.getByLabelText('Nome*')).toHaveValue('Fornecedor Y');
    expect(screen.getByLabelText('Site URL')).toHaveValue('');

    await userEvent.clear(screen.getByLabelText('Nome*'));
    await userEvent.type(screen.getByLabelText('Nome*'), '  Fornecedor Atualizado  ');
    await userEvent.type(screen.getByLabelText('Site URL'), 'meusite.com');

    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    expect(onSave).toHaveBeenCalledWith(9, {
      nome: 'Fornecedor Atualizado',
      site_url: 'http://meusite.com',
    });

    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }));
    expect(onClose).toHaveBeenCalled();
  });

  test('validates required name, minimum length and missing supplier id', async () => {
    const onSave = jest.fn();
    const { rerender } = render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X', site_url: '' }}
        onClose={() => {}}
        onSave={onSave}
        isLoading={false}
      />
    );

    await userEvent.clear(screen.getByLabelText('Nome*'));
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(showWarningToast).toHaveBeenCalledWith('Nome é obrigatório.');
    expect(onSave).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText('Nome*'), 'A');
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(showWarningToast).toHaveBeenCalledWith(
      'Nome deve ter pelo menos 2 caracteres.'
    );

    rerender(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ nome: 'Sem ID', site_url: '' }}
        onClose={() => {}}
        onSave={onSave}
        isLoading={false}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(showErrorToast).toHaveBeenCalledWith('Erro: ID do fornecedor não encontrado.');
  });

  test('opens import wizard and supports file actions on the files tab', async () => {
    render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X' }}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={false}
      />
    );

    expect(screen.getByTestId('wizard-state')).toHaveAttribute('data-open', 'false');

    fireEvent.click(screen.getByRole('button', { name: 'Importar Catálogo' }));
    fireEvent.click(screen.getAllByRole('button', { name: 'Importar Catálogo' })[1]);
    expect(screen.getByTestId('wizard-state')).toHaveAttribute('data-open', 'true');

    fireEvent.click(screen.getByText('close-wizard'));
    expect(screen.getByTestId('wizard-state')).toHaveAttribute('data-open', 'false');

    fireEvent.click(screen.getByRole('button', { name: 'Arquivos' }));

    await waitFor(() => {
      expect(fornecedorService.getCatalogImportFiles).toHaveBeenCalledWith({ fornecedor_id: 5 });
    });
    expect(screen.getByTestId('catalog-file-names')).toHaveTextContent('file1.csv');

    fireEvent.click(screen.getByText('reprocess-first'));
    fireEvent.click(screen.getByText('delete-first'));

    await waitFor(() => {
      expect(fornecedorService.reprocessCatalogFile).toHaveBeenCalledWith(1, {
        fornecedor_id: 5,
      });
      expect(fornecedorService.deleteCatalogFile).toHaveBeenCalledWith(1);
    });
  });

  test('logs failures while fetching and mutating catalog files', async () => {
    fornecedorService.getCatalogImportFiles.mockRejectedValueOnce(new Error('sem acesso'));
    fornecedorService.reprocessCatalogFile.mockRejectedValueOnce(new Error('falha no reprocessamento'));
    fornecedorService.deleteCatalogFile.mockRejectedValueOnce(new Error('falha na exclusao'));

    render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X' }}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={false}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Arquivos' }));

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Erro ao carregar arquivos de catálogo:',
        expect.any(Error)
      );
    });

    fornecedorService.getCatalogImportFiles.mockResolvedValue({ items: filesMock });
    fireEvent.click(screen.getByRole('button', { name: 'Info' }));
    fireEvent.click(screen.getByRole('button', { name: 'Arquivos' }));

    await screen.findByTestId('catalog-file-names');
    fireEvent.click(screen.getByText('reprocess-first'));
    fireEvent.click(screen.getByText('delete-first'));

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Erro ao reprocessar arquivo:',
        expect.any(Error)
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Erro ao excluir arquivo:',
        expect.any(Error)
      );
    });
  });
});
