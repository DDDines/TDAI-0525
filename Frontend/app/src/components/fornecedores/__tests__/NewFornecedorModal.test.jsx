import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import NewFornecedorModal from '../NewFornecedorModal.jsx';
import fornecedorService from '../../../services/fornecedorService';
import { showErrorToast, showWarningToast } from '../../../utils/notifications';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    resolveFornecedorLogo: jest.fn(),
  },
}));

jest.mock('../../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

describe('NewFornecedorModal', () => {
  const onClose = jest.fn();
  const onSave = jest.fn();
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    onSave.mockResolvedValue({});
    fornecedorService.resolveFornecedorLogo.mockResolvedValue({
      logo_url: 'https://cdn.example.com/logo.png',
      resolved_site_url: 'https://exemplo.com',
      source: 'img-logo',
    });
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  function renderModal(props = {}) {
    return render(
      <NewFornecedorModal
        isOpen={true}
        onClose={onClose}
        onSave={onSave}
        isLoading={false}
        {...props}
      />
    );
  }

  test('does not render when closed', () => {
    render(
      <NewFornecedorModal
        isOpen={false}
        onClose={onClose}
        onSave={onSave}
        isLoading={false}
      />
    );

    expect(screen.queryByText(/Novo Fornecedor/i)).not.toBeInTheDocument();
  });

  test('validates name before saving', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(screen.getByRole('button', { name: /^Salvar$/i }));
    expect(showWarningToast.mock.calls[0][0]).toMatch(/Nome .*obrigat.rio/i);

    await user.type(screen.getByLabelText(/Nome/i), 'A');
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }));
    expect(showWarningToast.mock.calls.at(-1)[0]).toMatch(/2 caracteres/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  test('normalizes url and clears the form after a successful save', async () => {
    const user = userEvent.setup();
    renderModal();

    const nomeInput = screen.getByLabelText(/Nome/i);
    const siteInput = screen.getByLabelText(/Site URL/i);

    await user.type(nomeInput, 'Fornecedor Teste');
    await user.type(siteInput, 'exemplo.com');
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith({
        nome: 'Fornecedor Teste',
        site_url: 'http://exemplo.com',
        logo_url: null,
      });
    });
    expect(nomeInput).toHaveValue('');
    expect(siteInput).toHaveValue('');
  });

  test('sends null site_url when the field is blank', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/Nome/i), 'Fornecedor Sem Site');
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith({
        nome: 'Fornecedor Sem Site',
        site_url: null,
        logo_url: null,
      });
    });
  });

  test('keeps already normalized urls unchanged', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/Nome/i), 'Fornecedor Seguro');
    await user.type(screen.getByLabelText(/Site URL/i), 'https://seguro.example');
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith({
        nome: 'Fornecedor Seguro',
        site_url: 'https://seguro.example',
        logo_url: null,
      });
    });
  });

  test('renders the loading state while save is in progress', () => {
    renderModal({ isLoading: true });

    expect(screen.getByRole('button', { name: /Salvando/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Fechar/i })).toBeDisabled();
  });

  test('keeps the form data when the save promise rejects', async () => {
    const user = userEvent.setup();
    onSave.mockRejectedValueOnce(new Error('falha'));
    renderModal();

    const nomeInput = screen.getByLabelText(/Nome/i);
    await user.type(nomeInput, 'Fornecedor Instavel');
    await user.click(screen.getByRole('button', { name: /^Salvar$/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalled();
    });
    expect(nomeInput).toHaveValue('Fornecedor Instavel');
  });

  test('resolves logo from the site and fills the dedicated field', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/Nome/i), 'Fornecedor Logo');
    await user.type(screen.getByLabelText(/Site URL/i), 'exemplo.com');
    await user.click(screen.getByRole('button', { name: /Buscar do site/i }));

    await waitFor(() => {
      expect(fornecedorService.resolveFornecedorLogo).toHaveBeenCalledWith(
        'http://exemplo.com'
      );
    });
    expect(screen.getByLabelText(/Logo URL/i)).toHaveValue('https://cdn.example.com/logo.png');
    expect(screen.getByAltText(/Logo de Fornecedor Logo/i)).toBeInTheDocument();
    expect(showErrorToast).not.toHaveBeenCalled();
  });
});
