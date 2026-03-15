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
    resolveFornecedorLogo: jest.fn(),
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
    fornecedorService.resolveFornecedorLogo.mockResolvedValue({
      logo_url: 'https://cdn.example.com/logo.png',
      resolved_site_url: 'https://fornecedor.test',
      source: 'img-logo',
    });
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
    expect(screen.getByLabelText('Logo URL')).toHaveValue('');

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

    fireEvent.click(screen.getByRole('button', { name: 'Salvar alteracoes' }));

    expect(onSave).toHaveBeenCalledWith(9, {
      nome: 'Fornecedor Atualizado',
      site_url: 'http://meusite.com',
      logo_url: null,
    });

    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }));
    expect(onClose).toHaveBeenCalled();
  });

  test('keeps fully qualified urls unchanged and supports raw file arrays from the service', async () => {
    fornecedorService.getCatalogImportFiles.mockResolvedValueOnce(filesMock);
    const onSave = jest.fn();

    render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X', site_url: 'https://fornecedor.test' }}
        onClose={() => {}}
        onSave={onSave}
        isLoading={false}
      />
    );

    await userEvent.clear(screen.getByLabelText('Nome*'));
    await userEvent.type(screen.getByLabelText('Nome*'), 'Fornecedor Seguro');
    await userEvent.clear(screen.getByLabelText('Site URL'));
    await userEvent.type(screen.getByLabelText('Site URL'), 'https://seguro.example');
    fireEvent.click(screen.getByRole('button', { name: /Salvar altera/i }));

    expect(onSave).toHaveBeenCalledWith(5, {
      nome: 'Fornecedor Seguro',
      site_url: 'https://seguro.example',
      logo_url: null,
    });

    fireEvent.click(screen.getByRole('button', { name: 'Arquivos' }));
    expect(await screen.findByTestId('catalog-file-names')).toHaveTextContent('file1.csv');
  });

  test('resolves and previews the supplier logo from the informed site', async () => {
    render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X', site_url: 'fornecedor.test' }}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={false}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Buscar do site/i }));

    await waitFor(() => {
      expect(fornecedorService.resolveFornecedorLogo).toHaveBeenCalledWith(
        'http://fornecedor.test'
      );
    });
    expect(screen.getByLabelText('Logo URL')).toHaveValue('https://cdn.example.com/logo.png');
    expect(screen.getByAltText(/Logo de Fornecedor X/i)).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alteracoes' }));
    expect(showWarningToast).toHaveBeenCalledWith('Nome e obrigatorio.');
    expect(onSave).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText('Nome*'), 'A');
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alteracoes' }));
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

    fireEvent.click(screen.getByRole('button', { name: 'Salvar alteracoes' }));
    expect(showErrorToast).toHaveBeenCalledWith('Erro: ID do fornecedor nao encontrado.');
    fireEvent.click(screen.getByRole('button', { name: 'Arquivos' }));
    expect(fornecedorService.getCatalogImportFiles).not.toHaveBeenCalled();
  });

  test('fills missing supplier fields with empty strings before editing', () => {
    render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 7, nome: null, site_url: null }}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={false}
      />
    );

    expect(screen.getByLabelText('Nome*')).toHaveValue('');
    expect(screen.getByLabelText('Site URL')).toHaveValue('');
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

    fireEvent.click(screen.getByRole('button', { name: 'Importar Catalogo' }));
    fireEvent.click(screen.getAllByRole('button', { name: 'Importar Catalogo' })[1]);
    expect(screen.getByTestId('wizard-state')).toHaveAttribute('data-open', 'true');

    fireEvent.click(screen.getByText('close-wizard'));
    expect(screen.getByTestId('wizard-state')).toHaveAttribute('data-open', 'false');

    fireEvent.click(screen.getByRole('button', { name: 'Arquivos' }));

    await waitFor(() => {
      expect(fornecedorService.getCatalogImportFiles).toHaveBeenCalledWith({ fornecedor_id: 5 });
    });
    expect(screen.getByTestId('catalog-file-names')).toHaveTextContent('file1.csv');

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar arquivo' }));
    expect(screen.getByTestId('wizard-state')).toHaveAttribute('data-open', 'true');

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
        'Erro ao carregar arquivos de catalogo:',
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

  test('shows the loading label while the modal save action is disabled', () => {
    render(
      <EditFornecedorModal
        isOpen={true}
        fornecedorData={{ id: 5, nome: 'Fornecedor X', site_url: '' }}
        onClose={() => {}}
        onSave={() => {}}
        isLoading={true}
      />
    );

    expect(screen.getByRole('button', { name: /Salvando/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Fechar' })).toBeDisabled();
  });
});

