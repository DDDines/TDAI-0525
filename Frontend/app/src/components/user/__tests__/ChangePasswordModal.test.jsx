import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ChangePasswordModal from '../ChangePasswordModal.jsx';
import authService from '../../../services/authService';
import { useAuth } from '../../../contexts/AuthContext';
import {
  showErrorToast,
  showSuccessToast,
} from '../../../utils/notifications';

jest.mock('../../../services/authService', () => ({
  __esModule: true,
  default: {
    changePassword: jest.fn(),
  },
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
}));

describe('ChangePasswordModal', () => {
  const onClose = jest.fn();
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    useAuth.mockReturnValue({
      user: { id: 42 },
    });
    authService.changePassword.mockResolvedValue({
      message: 'Senha atualizada no servidor.',
    });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  function renderModal(props = {}) {
    return render(
      <ChangePasswordModal
        isOpen={true}
        onClose={onClose}
        {...props}
      />
    );
  }

  test('does not render when closed', () => {
    render(<ChangePasswordModal isOpen={false} onClose={onClose} />);

    expect(screen.queryByText('Alterar Senha')).not.toBeInTheDocument();
  });

  test('validates missing user and password mismatch locally', async () => {
    useAuth.mockReturnValue({ user: null });
    const user = userEvent.setup();

    renderModal();

    await user.type(screen.getByLabelText(/Senha Atual/i), 'atual1234');
    await user.type(screen.getByLabelText(/^Nova Senha/i), 'nova12345');
    await user.type(screen.getByLabelText(/^Confirmar Nova Senha/i), 'nova12345');
    await user.click(screen.getByRole('button', { name: /Salvar Nova Senha/i }));

    expect(showErrorToast.mock.calls[0][0]).toMatch(/identificado/i);
    expect(authService.changePassword).not.toHaveBeenCalled();
  });

  test('validates minimum password length before submit', async () => {
    const user = userEvent.setup();

    renderModal();

    await user.type(screen.getByLabelText(/Senha Atual/i), 'atual1234');
    await user.type(screen.getByLabelText(/^Nova Senha/i), 'curta');
    await user.type(screen.getByLabelText(/^Confirmar Nova Senha/i), 'curta');
    await user.click(screen.getByRole('button', { name: /Salvar Nova Senha/i }));

    expect(showErrorToast.mock.calls[0][0]).toMatch(/8 caracteres/i);
    expect(authService.changePassword).not.toHaveBeenCalled();
  });

  test('submits successfully, clears the form and closes the modal', async () => {
    const user = userEvent.setup();

    renderModal();

    const currentPassword = screen.getByLabelText(/Senha Atual/i);
    const newPassword = screen.getByLabelText(/^Nova Senha/i);
    const confirmPassword = screen.getByLabelText(/^Confirmar Nova Senha/i);

    await user.type(currentPassword, 'atual1234');
    await user.type(newPassword, 'nova12345');
    await user.type(confirmPassword, 'nova12345');
    await user.click(screen.getByRole('button', { name: /Salvar Nova Senha/i }));

    await waitFor(() => {
      expect(authService.changePassword).toHaveBeenCalledWith(42, {
        current_password: 'atual1234',
        new_password: 'nova12345',
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Senha atualizada no servidor.');
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(currentPassword).toHaveValue('');
    expect(newPassword).toHaveValue('');
    expect(confirmPassword).toHaveValue('');
  });

  test('shows service errors without closing the modal', async () => {
    const user = userEvent.setup();
    authService.changePassword.mockRejectedValueOnce({
      detail: 'Senha atual incorreta.',
    });

    renderModal();

    await user.type(screen.getByLabelText(/Senha Atual/i), 'atual1234');
    await user.type(screen.getByLabelText(/^Nova Senha/i), 'nova12345');
    await user.type(screen.getByLabelText(/^Confirmar Nova Senha/i), 'nova12345');
    await user.click(screen.getByRole('button', { name: /Salvar Nova Senha/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Senha atual incorreta.');
    });
    expect(onClose).not.toHaveBeenCalled();
  });
});
